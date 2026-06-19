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
