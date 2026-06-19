"""Tests for Chinese i18n in OpenAPI schema."""


def test_system_router_has_chinese_tag(client):
    schema = client.get("/openapi.json").json()
    tag_names = [t["name"] for t in schema["tags"]]
    assert "服务状态" in tag_names


def test_system_status_has_chinese_summary(client):
    schema = client.get("/openapi.json").json()
    op = schema["paths"]["/api/system/status"]["get"]
    assert op["summary"] == "获取服务状态"


def test_tasks_router_has_chinese_tag(client):
    schema = client.get("/openapi.json").json()
    tag_names = [t["name"] for t in schema["tags"]]
    assert "定时任务" in tag_names


def test_tasks_endpoints_have_chinese_summaries(client):
    schema = client.get("/openapi.json").json()
    list_op = schema["paths"]["/api/tasks"]["get"]
    get_op = schema["paths"]["/api/tasks/{task_id}"]["get"]
    assert list_op["summary"] == "列出所有任务"
    assert get_op["summary"] == "查看单个任务"


def test_task_model_fields_have_chinese_descriptions(client):
    schema = client.get("/openapi.json").json()
    task_schema = schema["components"]["schemas"]["Task"]
    props = task_schema["properties"]
    # Every field should have a description and contain at least one CJK char
    for field_name, field_schema in props.items():
        assert "description" in field_schema, f"{field_name} 缺少 description"
        assert any('一' <= c <= '鿿' for c in field_schema["description"]), \
            f"{field_name} 的 description 不是中文: {field_schema['description']}"
