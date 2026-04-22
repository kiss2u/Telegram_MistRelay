from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .config_service import ConfigService


class ApiClient:
    def __init__(self, config_service: ConfigService) -> None:
        self._config_service = config_service

    def _server_base_url(self) -> str:
        base_url = self._config_service.config.server_base_url.strip()
        return base_url.rstrip("/")

    def _api_base_url(self) -> str:
        base_url = self._server_base_url()
        if not base_url:
            raise RuntimeError("请先配置服务端地址")
        return f"{base_url}/api"

    def _proxy(self) -> str | None:
        config = self._config_service.config
        if config.proxy.enabled and config.proxy.url.strip():
            return config.proxy.url.strip()
        return None

    def _headers(self, include_auth: bool = True) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = self._config_service.config.auth_token
        if include_auth and token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        include_auth: bool = True,
        timeout: float = 60.0,
    ) -> Any:
        kwargs: dict[str, Any] = {}
        proxy = self._proxy()
        if proxy:
            kwargs["proxy"] = proxy
        normalized_params = None
        if params is not None:
            normalized_params = {
                key: value
                for key, value in params.items()
                if value is not None and value != ""
            }

        with httpx.Client(
            base_url=self._api_base_url(),
            timeout=timeout,
            headers=self._headers(include_auth=include_auth),
            **kwargs,
        ) as client:
            response = client.request(method, path, params=normalized_params, json=payload)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and data.get("success") is False:
                raise RuntimeError(str(data.get("error") or data.get("message") or "请求失败"))
            return data

    def login(self, username: str, password: str) -> dict[str, Any]:
        data = self.request(
            "POST",
            "/auth/login",
            payload={"username": username, "password": password},
            include_auth=False,
        )
        token = data.get("token")
        if not token:
            raise RuntimeError(str(data.get("error") or "登录失败"))
        return data

    def get_current_user(self) -> dict[str, Any]:
        return self.request("GET", "/auth/me")

    def get_status(self) -> dict[str, Any]:
        return self.request("GET", "/status")

    def get_downloads(self, limit: int = 100, grouped: bool = True) -> dict[str, Any]:
        return self.request("GET", "/downloads", params={"limit": limit, "grouped": grouped})

    def get_uploads(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        upload_target: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "GET",
            "/uploads",
            params={
                "limit": limit,
                "status": status,
                "upload_target": upload_target,
            },
        )

    def get_download_statistics(self) -> dict[str, Any]:
        return self.request("GET", "/downloads/statistics")

    def get_upload_statistics(self) -> dict[str, Any]:
        return self.request("GET", "/uploads/statistics")

    def get_queue_status(self) -> dict[str, Any]:
        return self.request("GET", "/queue")

    def get_system_trend(self) -> dict[str, Any]:
        return self.request("GET", "/monitor/trend")

    def retry_download(self, gid: str) -> dict[str, Any]:
        return self.request("POST", f"/downloads/{gid}/retry")

    def delete_download(self, gid: str) -> dict[str, Any]:
        return self.request("DELETE", f"/downloads/{gid}")

    def delete_download_record(self, download_id: int, *, delete_file: bool = True) -> dict[str, Any]:
        return self.request(
            "DELETE",
            f"/downloads/record/{download_id}",
            params={"delete_file": delete_file},
        )

    def retry_upload(self, upload_id: int) -> dict[str, Any]:
        return self.request("POST", f"/uploads/{upload_id}/retry")

    def delete_upload(self, upload_id: int) -> dict[str, Any]:
        return self.request("DELETE", f"/uploads/{upload_id}")

    def delete_all_downloads(self) -> dict[str, Any]:
        return self.request("DELETE", "/downloads/all")

    def get_rclone_remotes(self) -> dict[str, Any]:
        return self.request("GET", "/rclone/remotes")

    def browse_drive(self, remote: str, path: str = "/") -> dict[str, Any]:
        return self.request(
            "GET",
            "/rclone/browse",
            params={"remote": remote, "path": path},
        )

    def get_drive_usage(self, remote: str) -> dict[str, Any]:
        return self.request("GET", "/rclone/about", params={"remote": remote})

    def get_thumbnail(
        self,
        *,
        remote: str,
        path: str,
        item_type: str,
        directory: str | None = None,
        item_id: str | None = None,
    ) -> dict[str, Any]:
        payload = self.request(
            "GET",
            "/rclone/thumbnail",
            params={
                "remote": remote,
                "path": path,
                "type": item_type,
                "dir": directory,
                "id": item_id,
            },
        )
        thumbnail_url = payload.get("thumbnail_url")
        if thumbnail_url:
            payload["thumbnail_url"] = self.resolve_server_url(thumbnail_url)
        return payload

    def delete_file(self, *, remote: str, path: str, is_dir: bool = False) -> dict[str, Any]:
        return self.request(
            "DELETE",
            "/rclone/file",
            params={"remote": remote, "path": path, "is_dir": is_dir},
        )

    def browse_telegram(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        search: str = "",
        media_type: str = "",
        sort_by: str = "time",
        sort_desc: bool = True,
    ) -> dict[str, Any]:
        return self.request(
            "GET",
            "/telegram/browse",
            params={
                "page": page,
                "page_size": page_size,
                "search": search,
                "type": media_type,
                "sort_by": sort_by,
                "sort_desc": sort_desc,
            },
        )

    def get_telegram_usage(self) -> dict[str, Any]:
        return self.request("GET", "/telegram/usage")

    def delete_telegram_item(self, message_id: int) -> dict[str, Any]:
        return self.request("DELETE", f"/telegram/item/{message_id}")

    def delete_telegram_group(self, media_group_id: str) -> dict[str, Any]:
        return self.request("DELETE", f"/telegram/group/{quote(media_group_id, safe='')}")

    def clear_telegram_media(self) -> dict[str, Any]:
        return self.request("DELETE", "/telegram/all")

    def get_config(self, category: str | None = None) -> dict[str, Any]:
        return self.request("GET", "/config", params={"category": category} if category else None)

    def update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/config", payload=payload)

    def reload_config(self) -> dict[str, Any]:
        return self.request("POST", "/config/reload")

    def get_docker_status(self) -> dict[str, Any]:
        return self.request("GET", "/system/docker/status")

    def restart_docker(self) -> dict[str, Any]:
        return self.request("POST", "/system/docker/restart")

    def get_docker_logs(self, *, lines: int = 100) -> dict[str, Any]:
        return self.request("GET", "/system/docker/logs", params={"lines": lines})

    def get_system_resources(self) -> dict[str, Any]:
        return self.request("GET", "/system/resources")

    def get_rclone_config(self) -> dict[str, Any]:
        return self.request("GET", "/rclone/config")

    def save_rclone_config(self, content: str) -> dict[str, Any]:
        return self.request("POST", "/rclone/config", payload={"content": content})

    def get_log_files(self) -> dict[str, Any]:
        return self.request("GET", "/logs/files")

    def get_log_content(
        self,
        *,
        file: str | None = None,
        tail: int | None = None,
        level: str | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "GET",
            "/logs",
            params={
                "file": file,
                "tail": tail,
                "level": level,
                "keyword": keyword,
            },
        )

    def get_log_download_url(self, filename: str) -> str:
        return self.resolve_server_url(f"/api/logs/download/{quote(filename, safe='')}")

    def download_log_file(self, filename: str, destination: Path) -> Path:
        kwargs: dict[str, Any] = {}
        proxy = self._proxy()
        if proxy:
            kwargs["proxy"] = proxy

        with httpx.Client(
            timeout=60.0,
            headers=self._headers(include_auth=True),
            **kwargs,
        ) as client:
            response = client.get(
                self.resolve_server_url(f"/api/logs/download/{quote(filename, safe='')}")
            )
            response.raise_for_status()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)
        return destination

    def resolve_server_url(self, path: str) -> str:
        clean_path = path if path.startswith("/") else f"/{path}"
        return f"{self._server_base_url()}{clean_path}"
