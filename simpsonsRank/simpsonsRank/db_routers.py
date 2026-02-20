class MongoRouter:
    """
    Envía modelos concretos a la BD 'mongodb' y deja el resto en 'default'.
    Ajusta la lista mongo_models a tus modelos "managed = False".
    """
    mongo_models = {"character", "episodes", "locations", "review", "ranking"}


    def db_for_read(self, model, **hints):
        if model._meta.model_name in self.mongo_models:
            return "mongodb"
        return "default"


    def db_for_write(self, model, **hints):
        if model._meta.model_name in self.mongo_models:
            return "mongodb"
        return "default"


    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name in self.mongo_models:
            return db == "mongodb"
        return db == "default"