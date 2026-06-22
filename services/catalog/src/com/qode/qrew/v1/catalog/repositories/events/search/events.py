from com.qode.qrew.v1.catalog.repositories.events.search.config import (
    SearchConfig,
    SearchField,
    Weight,
)

EVENTS_SEARCH_CONFIG = SearchConfig(
    name="events",
    table="catalog.events",
    fields=[
        SearchField("name", Weight.A),
        SearchField("description", Weight.B),
        SearchField("organiser_name", Weight.C),
        SearchField("venue_city", Weight.C),
    ],
    language="simple",
)
