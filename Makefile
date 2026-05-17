.PHONY: help install dev lint format test run cli migrate

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	uv sync

dev: ## 安装开发依赖
	uv sync --dev

lint: ## 代码检查
	uv run ruff check src/ tests/

format: ## 代码格式化
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

test: ## 运行测试
	uv run pytest tests/ -v

run: ## 启动开发服务器
	uv run python -m src.api.run

cli: ## 运行 CLI
	uv run python -m src.cli.main $(ARGS)

migrate: ## 执行数据库迁移
	uv run alembic upgrade head

migrate-new: ## 创建新迁移脚本
	uv run alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## 回滚上一次迁移
	uv run alembic downgrade -1
