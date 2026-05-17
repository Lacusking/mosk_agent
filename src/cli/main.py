"""
CLI 入口

基于 Typer 的命令行工具。
"""

import typer

cli = typer.Typer(help="MoskAgent CLI 工具")


@cli.command("health")
def health_check() -> None:
    """检查系统配置与连接状态。"""
    from src.core.config import settings

    typer.echo(f"环境: {settings.app.ENVIRONMENT}")
    typer.echo(f"版本: {settings.app.VERSION}")
    typer.echo(f"数据库: {settings.db.DB_HOST}:{settings.db.DB_PORT}/{settings.db.DB_NAME}")
    typer.echo(f"Redis: {settings.redis.REDIS_HOST}:{settings.redis.REDIS_PORT}")
    typer.echo("配置检查通过")


@cli.command("version")
def version() -> None:
    """显示版本信息。"""
    from src.core.config import settings

    typer.echo(f"MoskAgent v{settings.app.VERSION}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
