from datetime import datetime, date ,time
from decimal import Decimal
from uuid import UUID

def model_to_dict(model_instance, exclude=None, relationship_depth=1, exclude_relationships=None):
    """
    Convert SQLAlchemy model instance to dictionary with smart defaults.
    
    Args:
        model_instance: SQLAlchemy model instance
        exclude: Fields to exclude (e.g., passwords)
        relationship_depth: 0 = no relationships, 1 = first level, 2 = nested
        exclude_relationships: Specific relationships to exclude
    
    Returns:
        dict: Clean dictionary representation
    """
    if model_instance is None:
        return None
    
    if exclude is None:
        exclude = []
    if exclude_relationships is None:
        exclude_relationships = []
    
    result = {}
    
    # Get column values
    for column in model_instance.__table__.columns:
        col_name = column.name
        if col_name in exclude:
            continue
            
        value = getattr(model_instance, col_name)
        
        # Handle common serialization issues
        if value is None:
            result[col_name] = None
        elif isinstance(value, datetime):
            result[col_name] = value.isoformat()
        elif isinstance(value, date):
            result[col_name] = value.isoformat()
        elif isinstance(value, time):
            result[col_name] = value.isoformat()
        elif isinstance(value, Decimal):
            result[col_name] = float(value)
        elif isinstance(value, UUID):
            result[col_name] = str(value)
        else:
            result[col_name] = value
    
    # Handle relationships
    if relationship_depth > 0:
        for rel_name, relationship in model_instance.__mapper__.relationships.items():
            if rel_name in exclude_relationships:
                continue
                
            related = getattr(model_instance, rel_name)
            
            if related is None:
                result[rel_name] = None
            elif isinstance(related, list):
                result[rel_name] = [
                    model_to_dict(
                        item,
                        exclude=exclude,
                        relationship_depth=relationship_depth - 1,
                        exclude_relationships=exclude_relationships
                    )
                    for item in related
                ]
            else:
                result[rel_name] = model_to_dict(
                    related,
                    exclude=exclude,
                    relationship_depth=relationship_depth - 1,
                    exclude_relationships=exclude_relationships
                )
    
    return result