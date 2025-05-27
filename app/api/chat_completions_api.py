import httpx
import json
import threading
import asyncio
import queue
from abc import ABC, abstractmethod

from app.events import DataEvent, DataEventType
from app.utils.utils import create_logger
from app.context import context

base_client_log = create_logger(__name__, entity_name='BASE_HTTP_CLIENT', level=context.log_level)

class BaseHttpxClientWrapper(ABC):
    def __init__(self, endpoint: str, api_key: str = None, default_headers: dict = None, logger=None):
        self.logger = logger if logger else base_client_log
        self.logger.debug(f"Initializing {self.__class__.__name__} with endpoint: {endpoint}")
        self.endpoint = endpoint
        self.api_key = api_key
        self.base_url = endpoint
        
        self.default_headers = default_headers if default_headers is not None else {}
        if self.api_key and "Authorization" not in self.default_headers:
            self.default_headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.stop_event = threading.Event()
        self.logger.debug(f"{self.__class__.__name__} initialized.")

    def stop(self):
        """Signals the active streaming request to stop."""
        self.logger.debug("Stopping active stream request.")
        self.stop_event.set()

    def _prepare_client_kwargs(self, proxies: dict = None) -> dict:
        """Prepares keyword arguments (mounts, timeout) for httpx.AsyncClient."""
        timeout_config = httpx.Timeout(connect=60.0, read=300.0, write=60.0, pool=60.0)
        client_mounts = None
        if proxies:
            temp_mounts = {}
            for scheme_key, proxy_url_value in proxies.items():
                if proxy_url_value:
                    mount_key_url_prefix = None
                    if scheme_key.lower() == 'http':
                        mount_key_url_prefix = 'http://'
                    elif scheme_key.lower() == 'https':
                        mount_key_url_prefix = 'https://'
                    elif scheme_key.lower() == 'all':
                        mount_key_url_prefix = 'all://'
                    
                    if mount_key_url_prefix:
                        try:
                            temp_mounts[mount_key_url_prefix] = httpx.HTTPTransport(proxy=proxy_url_value)
                        except Exception as e_transport_init:
                            self.logger.debug(f"Error initializing HTTPTransport for {mount_key_url_prefix} with proxy URL {proxy_url_value}: {e_transport_init}")
                    else:
                        self.logger.debug(f"Proxy configuration: Unsupported scheme key '{scheme_key}'. This key will be ignored.")
            if temp_mounts:
                client_mounts = temp_mounts
        return {"mounts": client_mounts, "timeout": timeout_config}

    @abstractmethod
    async def _process_stream_response_async(self, res: httpx.Response, quiet: bool):
        """Processes a streaming response. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def _process_non_stream_response_async(self, res: httpx.Response, quiet: bool):
        """Processes a non-streaming response. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _get_request_url(self, **kwargs) -> str:
        """Constructs the specific request URL. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _prepare_request_payload(self, **kwargs) -> dict:
        """Constructs the request payload. Must be implemented by subclasses."""
        pass

    async def _execute_request_async_worker(self, data_queue: queue.Queue, request_url: str, payload: dict, stream: bool, quiet: bool, proxies: dict = None, method: str = "POST"):
        """The actual async worker that makes requests and processes responses."""
        res_for_closing = None
        try:
            if self.stop_event.is_set():
                self.logger.debug("Async worker: Request cancelled by stop_event before sending.")
                data_queue.put(DataEvent(DataEventType.INFO, "Request cancelled before sending.", quiet))
                return

            client_kwargs = self._prepare_client_kwargs(proxies)
            request_headers = self.default_headers.copy()

            async with httpx.AsyncClient(**client_kwargs) as client:
                if stream:
                    self.logger.debug(f"Async worker: Making STREAMING {method} request to {request_url}")
                    async with client.stream(method, request_url, json=payload, headers=request_headers) as res:
                        self.logger.debug(f"Stream request opened. Status: {res.status_code}")
                        res.raise_for_status()
                        self.logger.debug("Async worker: Stream request successful, processing response.")
                        async for event in self._process_stream_response_async(res, quiet):
                            if self.stop_event.is_set():
                                self.logger.debug("Async worker: Stream stopped by stop_event during processing.")
                                data_queue.put(DataEvent(DataEventType.INFO, "Stream stopped by user.", quiet))
                                raise asyncio.CancelledError("Stream stopped by user via stop_event.")
                            data_queue.put(event)
                else:
                    self.logger.debug(f"Async worker: Making NON-STREAMING {method} request to {request_url}")
                    res_non_stream = await client.request(method, request_url, json=payload, headers=request_headers)
                    res_for_closing = res_non_stream
                    self.logger.debug(f"Non-stream request completed. Status: {res_non_stream.status_code}")
                    res_non_stream.raise_for_status()
                    self.logger.debug("Async worker: Non-stream request successful, processing response.")
                    async for event in self._process_non_stream_response_async(res_non_stream, quiet):
                        if self.stop_event.is_set():
                            self.logger.debug("Async worker: Non-stream processing stopped by stop_event.")
                            data_queue.put(DataEvent(DataEventType.INFO, "Request stopped by user.", quiet))
                            raise asyncio.CancelledError("Non-stream processing stopped by user via stop_event.")
                        data_queue.put(event)

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Async worker: HTTPStatusError: {e.response.status_code} - {e.response.text}", exc_info=True)
            try:
                error_detail = e.response.json()
            except json.JSONDecodeError:
                error_detail = e.response.text
            data_queue.put(DataEvent(DataEventType.ERROR, f"API Error {e.response.status_code}: {error_detail}"))
        except httpx.RequestError as e:
            self.logger.error(f"Async worker: httpx.RequestError: {e}", exc_info=True)
            data_queue.put(DataEvent(DataEventType.ERROR, f"Request Error: {e}"))
        except asyncio.CancelledError as e:
            self.logger.debug(f"Async worker: Task was cancelled: {e}")
            data_queue.put(DataEvent(DataEventType.INFO, f"Request cancelled: {e}", quiet))
        except Exception as e:
            self.logger.error(f"Async worker: Unexpected error: {e}", exc_info=True)
            data_queue.put(DataEvent(DataEventType.ERROR, f"Unexpected error in async worker: {e}"))
        finally:
            if res_for_closing and hasattr(res_for_closing, 'aclose') and callable(res_for_closing.aclose):
                try:
                    if not res_for_closing.is_closed:
                        await res_for_closing.aclose()
                        self.logger.debug("Async worker: Non-streaming httpx.Response closed in finally.")
                except Exception as e_close:
                    self.logger.debug(f"Async worker: Error closing non-streaming httpx.Response: {e_close}")
            data_queue.put(None)

    def _execute_request_sync(self, stream: bool, quiet: bool, proxies: dict = None, method: str = "POST", **kwargs):
        self.logger.debug(f"Execute sync called. Stream: {stream}, Quiet: {quiet}")
        self.stop_event.clear()
        self.logger.debug("Stop event cleared for new request.")

        request_url = self._get_request_url(**kwargs)
        payload = self._prepare_request_payload(stream=stream, **kwargs)

        self.logger.debug(f"Request URL: {request_url}, Payload: {json.dumps(payload, indent=2)}")
        yield DataEvent(DataEventType.INFO, f'{self.__class__.__name__} request: {json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)}', quiet)
        
        if self.stop_event.is_set():
            self.logger.debug("Request cancelled by stop_event before starting worker thread.")
            yield DataEvent(DataEventType.INFO, "Request cancelled before sending.", quiet)
            return

        data_queue = queue.Queue()
        worker_context = {'loop': None, 'task': None}

        def worker_thread_target():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            worker_context['loop'] = loop
            
            async_task = self._execute_request_async_worker(
                data_queue, request_url, payload, stream, quiet, proxies, method
            )
            worker_context['task'] = loop.create_task(async_task)
            
            try:
                loop.run_until_complete(worker_context['task'])
            except asyncio.CancelledError:
                 self.logger.debug("Async worker task was cancelled in event loop.")
            except Exception as e_loop:
                self.logger.error(f"Exception in worker_thread_target event loop: {e_loop}", exc_info=True)
                data_queue.put(DataEvent(DataEventType.ERROR, f"Critical error in async worker thread: {e_loop}"))
                data_queue.put(None)
            finally:
                try:
                    remaining_tasks = asyncio.all_tasks(loop=loop)
                    if remaining_tasks:
                        tasks_to_gather = [t for t in remaining_tasks if t is not worker_context['task'] or not t.done()]
                        if tasks_to_gather:
                            loop.run_until_complete(asyncio.gather(*tasks_to_gather, return_exceptions=True))
                    
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception as e_shutdown:
                     self.logger.debug(f"Error during worker loop shutdown: {e_shutdown}")
                finally:
                    loop.close()
                    self.logger.debug("Asyncio event loop in worker thread closed.")
        
        thread = threading.Thread(target=worker_thread_target, daemon=True)
        thread.start()
        self.logger.debug("Async worker thread started.")

        try:
            while True:
                if self.stop_event.is_set() and worker_context.get('loop') and worker_context.get('task'):
                    loop = worker_context['loop']
                    task_to_cancel = worker_context['task']
                    if loop.is_running() and not task_to_cancel.done():
                        self.logger.debug("Main thread: stop_event is set. Requesting cancellation of async task.")
                        loop.call_soon_threadsafe(task_to_cancel.cancel)
                
                try:
                    event = data_queue.get(timeout=0.1)
                except queue.Empty:
                    if not thread.is_alive() and data_queue.empty():
                        self.logger.error("Worker thread terminated unexpectedly and queue is empty.")
                        yield DataEvent(DataEventType.ERROR, "Worker thread terminated unexpectedly.")
                        break
                    continue

                if event is None:
                    self.logger.debug("Received sentinel from async worker. Ending request.")
                    break
                yield event
        finally:
            self.logger.debug("Main thread: Exiting event loop. Ensuring worker thread is joined.")
            if thread.is_alive():
                if self.stop_event.is_set() and worker_context.get('loop') and worker_context.get('task'):
                    loop = worker_context['loop']
                    task_to_cancel = worker_context['task']
                    if loop.is_running() and not task_to_cancel.done():
                        loop.call_soon_threadsafe(task_to_cancel.cancel)
                
                thread.join(timeout=5.0)
                if thread.is_alive():
                    self.logger.warning("Worker thread did not terminate after join timeout.")
            else:
                thread.join()
            self.logger.debug(f"Exiting {self.__class__.__name__} sync request method.")


# --- OpenAI Specific Implementation ---
openai_chat_completions_log = create_logger(__name__, entity_name='OPENAI_CHAT_COMPLETIONS', level=context.log_level)

class OpenAICompletions(BaseHttpxClientWrapper):
    def __init__(self, endpoint: str, api_key: str):
        super().__init__(endpoint, api_key,
                         default_headers={"content-type": "application/json"},
                         logger=openai_chat_completions_log)
        
    def _get_request_url(self, **kwargs) -> str:
        return f"{self.base_url}/chat/completions"

    def _prepare_request_payload(self, messages: list, model: str, max_tokens: int,
                                 stop_sequences: list, temperature: float, top_p: float,
                                 stream: bool, frequency_penalty: float, logit_bias: dict,
                                 logprobs: bool, top_logprobs: int, max_completion_tokens: int,
                                 n: int, presence_penalty: float, response_format: dict,
                                 seed: int, service_tier: str, tools: list, tool_choice: str,
                                 parallel_tool_calls: bool, user: str, **kwargs) -> dict:
        """Constructs the payload for the OpenAI API request."""
        self.logger.debug("Preparing payload for OpenAI API request.")
        payload = {
            'model': model, 'messages': messages, 'stop': stop_sequences,
            'stream': stream, 'temperature': temperature, 'top_p': top_p,
            'max_tokens': max_tokens, 'frequency_penalty': frequency_penalty, 'logit_bias': logit_bias,
            'logprobs': logprobs, 'top_logprobs': top_logprobs, 'max_completion_tokens': max_completion_tokens,
            'n': n, 'presence_penalty': presence_penalty, 'response_format': response_format,
            'seed': seed, 'service_tier': service_tier, 'tools': tools, 'tool_choice': tool_choice,
            'parallel_tool_calls': parallel_tool_calls, 'user': user
        }
        filtered_payload = {k: v for k, v in payload.items() if v is not None}
        self.logger.debug(f"Prepared payload: {json.dumps(filtered_payload, indent=2)}")
        return filtered_payload

    async def _process_stream_response_async(self, res: httpx.Response, quiet: bool):
        """Processes a streaming response from the OpenAI API using httpx."""
        self.logger.debug("Processing OpenAI async stream response.")
        current_content = ""
        tool_calls_accumulator = {}
        finish_reason = None
        usage = None
        response_model_from_stream = None
        message_started = False

        async for line in res.aiter_lines():
            if self.stop_event.is_set():
                self.logger.debug("Stream stop event set by user (OpenAI async).")
                yield DataEvent(DataEventType.INFO, "Stream stopped by user.", quiet)
                break

            if line:
                line_str = line.strip()
                self.logger.debug(f"Received stream line: '{line_str[:100]}{'...' if len(line_str) > 100 else ''}'")
                if not line_str:
                    continue
                elif line_str == 'data: [DONE]':
                    self.logger.debug("Stream finished with [DONE].")
                    yield DataEvent(DataEventType.MESSAGE_END, None, quiet)
                    break
                elif line_str.startswith('data: '):
                    data_str = line_str[len('data: '):]
                    try:
                        data_dict = json.loads(data_str)
                        self.logger.debug(f"Parsed stream data: {data_dict}")

                        if not response_model_from_stream and "model" in data_dict:
                            response_model_from_stream = data_dict["model"]
                            self.logger.debug(f"Captured model from stream: {response_model_from_stream}")
                        
                        if not isinstance(data_dict, dict):
                            self.logger.debug("Parsed data is not a dict, skipping.")
                            continue

                        if "usage" in data_dict:
                            usage = data_dict["usage"]
                            self.logger.debug(f"Stream usage update: {usage}")

                        if not data_dict.get("choices"):
                            self.logger.debug("No 'choices' in stream data, skipping.")
                            continue

                        choice = data_dict["choices"][0]
                        delta = choice.get("delta", {})
                        self.logger.debug(f"Stream delta: {delta}")

                        if "content" in delta and delta["content"] is not None:
                            if not message_started:
                                message_started = True
                                self.logger.debug("Message start detected in stream.")
                                yield DataEvent(DataEventType.MESSAGE_START, None, quiet)
                                
                            content_chunk = delta["content"]
                            current_content += content_chunk
                            self.logger.debug(f"Content delta received: '{content_chunk[:50]}{'...' if len(content_chunk) > 50 else ''}'")
                            yield DataEvent(DataEventType.MESSAGE_DELTA, current_content, quiet)

                        if "tool_calls" in delta:
                            self.logger.debug(f"Tool calls delta received: {delta['tool_calls']}")
                            for tool_call_chunk in delta["tool_calls"]:
                                index = tool_call_chunk["index"]
                                
                                if index not in tool_calls_accumulator:
                                    tool_calls_accumulator[index] = {
                                        "id": tool_call_chunk.get("id", ""),
                                        "type": tool_call_chunk.get("type", "function"),
                                        "function": {"name": "", "arguments": ""}
                                    }
                                    self.logger.debug(f"New tool call at index {index} initialized with chunk: {tool_call_chunk}")
                                
                                current_tool_call = tool_calls_accumulator[index]

                                if "id" in tool_call_chunk and tool_call_chunk["id"]:
                                    current_tool_call["id"] = tool_call_chunk["id"]
                                if "type" in tool_call_chunk and tool_call_chunk["type"]:
                                    current_tool_call["type"] = tool_call_chunk["type"]
                                
                                if "function" in tool_call_chunk:
                                    if "name" in tool_call_chunk["function"] and tool_call_chunk["function"]["name"]:
                                        current_tool_call["function"]["name"] += tool_call_chunk["function"]["name"]
                                    if "arguments" in tool_call_chunk["function"] and tool_call_chunk["function"]["arguments"]:
                                        current_tool_call["function"]["arguments"] += tool_call_chunk["function"]["arguments"]
                                
                                self.logger.debug(f"Updated tool call at index {index}: {current_tool_call}")
                                yield DataEvent(DataEventType.TOOL_CALL_DELTA, {"index": index, "chunk": tool_call_chunk, "accumulated": current_tool_call}, quiet)

                        if choice.get("finish_reason"):
                            finish_reason = choice["finish_reason"]
                            self.logger.debug(f"Stream finish reason: {finish_reason}")
                            if finish_reason == "tool_calls":
                                self.logger.debug(f"Processing tool_calls finish reason. Accumulator: {tool_calls_accumulator}")
                                for index, tool_call in sorted(tool_calls_accumulator.items()):
                                     self.logger.debug(f"Yielding TOOL_CALL_COMPLETE for index {index}: {tool_call}")
                                     yield DataEvent(DataEventType.TOOL_CALL_COMPLETE, tool_call, quiet)
                                tool_calls_accumulator = {}
                                self.logger.debug("Tool calls accumulator cleared after 'tool_calls' finish_reason.")

                    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
                        self.logger.error(f"Stream parsing error: {e} in data: {data_str}", exc_info=True)
                        yield DataEvent(DataEventType.ERROR, f"Stream parsing error: {e} in data: {data_str}")
                        continue
                else:
                    self.logger.debug(f"Received non-data line: {line_str}")
                    yield DataEvent(DataEventType.INFO, f"Received non-data line: {line_str}", True)
        
        self.logger.debug(f"Stream processing finished. Current content length: {len(current_content)}. Finish reason: {finish_reason}")
        if message_started:
             yield DataEvent(DataEventType.STREAMED_MESSAGE_COMPLETE, current_content, quiet)

        if finish_reason != "tool_calls" and tool_calls_accumulator:
             self.logger.debug(f"Processing remaining tool calls after stream end (finish_reason: {finish_reason}). Accumulator: {tool_calls_accumulator}")
             for index, tool_call in sorted(tool_calls_accumulator.items()):
                 self.logger.debug(f"Yielding TOOL_CALL_COMPLETE for index {index} (post-stream): {tool_call}")
                 yield DataEvent(DataEventType.TOOL_CALL_COMPLETE, tool_call, quiet)
             tool_calls_accumulator = {}
             self.logger.debug("Tool calls accumulator cleared post-stream.")

        if usage or finish_reason or response_model_from_stream:
            metadata = {"usage": usage, "finish_reason": finish_reason}
            if response_model_from_stream:
                metadata["model"] = response_model_from_stream
            self.logger.debug(f"Yielding METADATA_RECEIVED: {metadata}")
            yield DataEvent(DataEventType.METADATA_RECEIVED, metadata, quiet)
        
        self.logger.debug("Exiting _process_stream_response_async (OpenAI).")


    async def _process_non_stream_response_async(self, res: httpx.Response, quiet: bool):
        """Processes a non-streaming response from the OpenAI API using httpx."""
        self.logger.debug("Processing OpenAI async non-stream response.")
        if self.stop_event.is_set():
            self.logger.debug("Request stopped before processing non-streaming response (OpenAI async).")
            yield DataEvent(DataEventType.INFO, "Request stopped before processing non-streaming response.", quiet)
            return

        try:
            res_json = res.json()
            self.logger.debug(f"Parsed async non-stream response JSON: {res_json}")

            if not res_json.get("choices"):
                 self.logger.error(f"No 'choices' in non-stream response: {res_json}")
                 yield DataEvent(DataEventType.ERROR, f"No 'choices' in response: {res_json}")
                 return

            choice = res_json["choices"][0]
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason")
            usage = res_json.get("usage")
            response_model_from_api = res_json.get("model")
            self.logger.debug(f"Non-stream choice (OpenAI async): {choice}, message: {message}, finish_reason: {finish_reason}, usage: {usage}, model: {response_model_from_api}")

            if message.get("content"):
                self.logger.debug(f"Non-stream message content (OpenAI async): '{str(message['content'])[:100]}{'...' if len(str(message['content'])) > 100 else ''}'")
                yield DataEvent(DataEventType.MESSAGE_COMPLETE, message["content"], quiet)

            if message.get("tool_calls"):
                self.logger.debug(f"Non-stream tool calls (OpenAI async): {message['tool_calls']}")
                for tool_call in message["tool_calls"]:
                    self.logger.debug(f"Yielding TOOL_CALL_COMPLETE for (OpenAI async): {tool_call}")
                    yield DataEvent(DataEventType.TOOL_CALL_COMPLETE, tool_call, quiet)
            
            metadata = {"usage": usage, "finish_reason": finish_reason}
            if response_model_from_api:
                metadata["model"] = response_model_from_api
            self.logger.debug(f"Yielding METADATA_RECEIVED (OpenAI async): {metadata}")
            yield DataEvent(DataEventType.METADATA_RECEIVED, metadata, quiet)

        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            self.logger.error(f"Async non-stream response parsing error: {e} in response: {res.text}", exc_info=True)
            yield DataEvent(DataEventType.ERROR, f"Response parsing error: {e} in response: {res.text}")
        self.logger.debug("Exiting _process_non_stream_response_async (OpenAI).")

    def create(self, messages: list, model: str,
               max_tokens: int = None,
               stop_sequences: list = None,
               temperature: float = None,
               top_p: float = None,
               stream: bool = False,
               frequency_penalty: float = None,
               logit_bias: dict = None,
               logprobs: bool = False,
               top_logprobs: int = None,
               max_completion_tokens: int = None,
               n: int = None,
               presence_penalty: float = None,
               response_format: dict = None,
               seed: int = None,
               service_tier: str = None,
               tools: list = None,
               tool_choice: str = None,
               parallel_tool_calls: bool = None,
               user: str = None,
               quiet: bool = False,
               proxies: dict = None,
               **kwargs):
        
        self.logger.debug(f"OpenAI Create called with model: {model}, stream: {stream}, quiet: {quiet}")
        
        all_params = {
            "messages": messages, "model": model, "max_tokens": max_tokens,
            "stop_sequences": stop_sequences, "temperature": temperature, "top_p": top_p,
            "frequency_penalty": frequency_penalty, "logit_bias": logit_bias,
            "logprobs": logprobs, "top_logprobs": top_logprobs,
            "max_completion_tokens": max_completion_tokens, "n": n,
            "presence_penalty": presence_penalty, "response_format": response_format,
            "seed": seed, "service_tier": service_tier, "tools": tools, "tool_choice": tool_choice,
            "parallel_tool_calls": parallel_tool_calls, "user": user,
            **kwargs
        }

        yield from self._execute_request_sync(
            stream=stream,
            quiet=quiet,
            proxies=proxies,
            method="POST",
            **all_params
        )