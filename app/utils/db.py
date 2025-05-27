from typing import List, Any, Optional
from flask_sqlalchemy.model import Model
from app.extensions import db

def add_and_commit(entity: Model):
    db.session.add(entity)
    db.session.commit()
    
    
def add_changes(entity: Model):
    db.session.add(entity)
    
    
def commit_changes():
    db.session.commit()
    
    
def delete_entity(entity: Model):
    db.session.delete(entity)


def get_entity_by_key(entity: Model, key_value: Any) -> Optional[Model]:
    return entity.query.get(key_value)
    

def get_entities_by_field(entity: Model, field: Any, field_value: Any) -> List[Model]:
    return entity.query.filter(field==field_value)
    

def get_entities_by_field_with_order(entity: Model, field: Any, field_value: Any, order_by_field: Any) -> List[Model]:
    return entity.query.filter(field==field_value).order_by(order_by_field)

def get_all_entity_ids(entity: Model) -> List[Any]:
    return [result[0] for result in db.session.query(entity.id).all()]

def get_all_entities(entity: Model) -> List[Model]:
    return db.session.query(entity).all()
    