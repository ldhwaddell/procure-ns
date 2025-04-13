from dagster import Definitions

from ingestion.definitions import defs as ingestion_definitions


defs = Definitions.merge(ingestion_definitions)
