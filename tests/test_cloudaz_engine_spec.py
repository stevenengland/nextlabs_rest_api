from __future__ import annotations

from nextlabs_sdk._cloudaz._component_models import ComponentLite, ComponentNameEntry
from nextlabs_sdk._cloudaz._engine._constructors import (
    query_paginated,
    search_paginated,
)
from nextlabs_sdk._cloudaz._search import SearchCriteria


def test_query_paginated_builds_get_plan():
    # given a query-paged spec with a templated path
    spec = query_paginated(
        ComponentNameEntry,
        "/console/api/v1/component/search/listNames/{group}",
    )
    # when a plan is built for page 0 with a page size
    plan = spec.plan_builder({"group": "RESOURCE"}, 0, 50)
    # then it is a GET with interpolated path and dialect params
    assert plan.method == "GET"
    assert plan.path == "/console/api/v1/component/search/listNames/RESOURCE"
    assert plan.params == {"pageNo": 0, "pageSize": 50}
    assert plan.json is None


def test_query_paginated_omits_page_size_when_none():
    spec = query_paginated(
        ComponentNameEntry,
        "/console/api/v1/component/search/listNames/{group}",
    )
    plan = spec.plan_builder({"group": "RESOURCE"}, 0, None)
    assert plan.params == {"pageNo": 0}


def test_search_paginated_builds_post_plan():
    spec = search_paginated(ComponentLite, "/console/api/v1/component/search")
    criteria = SearchCriteria().filter_group("RESOURCE")
    plan = spec.plan_builder({"criteria": criteria}, 0, None)
    assert plan.method == "POST"
    assert plan.path == "/console/api/v1/component/search"
    assert plan.params is None
    assert plan.json == criteria.page(0).to_dict()
