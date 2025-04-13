import dagster as dg

import psycopg2


class DataWarehouseResource(dg.ConfigurableResource):
    username: str
    password: str
    db: str

    def connect(self) -> psycopg2.extensions.connection:
        return psycopg2.connect(
            host="dwh",  # matches `hostname` and `container_name`
            port=5432,  # default Postgres port
            user=self.username,
            password=self.password,
            dbname=self.db,
        )
