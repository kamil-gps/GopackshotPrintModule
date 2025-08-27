from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional


class AblyLink:
	"""Lightweight wrapper around Ably Realtime for this app.

	Callbacks:
	- on_message(name, data)
	- on_status(status, err)
	"""

	def __init__(
		self,
		api_key: Optional[str] = None,
		auth_url: Optional[str] = None,
		client_id: Optional[str] = None,
		channel: str = "gopackshot:print-module:default",
		on_message: Optional[Callable[[str, Any], None]] = None,
		on_status: Optional[Callable[[str, Optional[str]], None]] = None,
		logger: Optional[Any] = None,
	):
		self.api_key = api_key
		self.auth_url = auth_url
		self.client_id = client_id
		self.channel_name = channel
		self.on_message = on_message
		self.on_status = on_status
		self.logger = logger
		self._ably = None
		self._channel = None
		self._lock = threading.RLock()
		self._last_err: Optional[str] = None
		self._started = False

	def _emit_status(self, status: str, err: Optional[str] = None) -> None:
		if self.on_status:
			try:
				self.on_status(status, err)
			except Exception:
				pass

	def start(self) -> None:
		with self._lock:
			if self._started:
				return
			self._started = True
		try:
			self._emit_status("connecting", None)
			import ably
			# Prefer Realtime client for subscriptions
			opts: dict[str, Any] = {}
			if self.client_id:
				opts["client_id"] = self.client_id
			if self.auth_url:
				opts["auth_url"] = self.auth_url
			elif self.api_key:
				opts["key"] = self.api_key
			else:
				raise ValueError("Ably requires auth_url or api_key")
			self._ably = ably.Realtime(**opts)

			# Connection state listeners
			def _conn_handler(state_change):
				try:
					state = getattr(state_change, "current", None) or getattr(state_change, "state", None)
					reason = getattr(getattr(state_change, "reason", None), "message", None)
					if reason is None and getattr(state_change, "reason", None):
						reason = str(state_change.reason)
					op = str(state).lower() if state else "unknown"
					self._emit_status(op, reason)
				except Exception:
					pass

			self._ably.connection.on(_conn_handler)

			# Channel setup and subscription
			self._channel = self._ably.channels.get(self.channel_name)

			def _msg_handler(msg):
				try:
					name = getattr(msg, "name", None) or getattr(msg, "event", None) or "message"
					data = getattr(msg, "data", None)
					if self.on_message:
						self.on_message(name, data)
				except Exception as exc:
					self._last_err = str(exc)
					if self.logger:
						self.logger.warning("Ably on_message error: %s", exc)

			self._channel.subscribe(_msg_handler)
			# Force connection attempt
			# Accessing connection.state triggers lazy connection; publish will also do
			_ = self._ably.connection.state
		except Exception as exc:
			self._last_err = str(exc)
			self._emit_status("error", self._last_err)
			if self.logger:
				self.logger.error("Ably start failed: %s", exc)

	def stop(self) -> None:
		with self._lock:
			if not self._started:
				return
			self._started = False
		try:
			if self._channel is not None:
				try:
					self._channel.unsubscribe()
				except Exception:
					pass
			if self._ably is not None:
				try:
					self._ably.close()
				except Exception:
					pass
			self._emit_status("disconnected", None)
		except Exception:
			pass

	def publish(self, name: str, data: Any) -> bool:
		try:
			if not self._channel:
				raise RuntimeError("Ably channel not ready")
			self._channel.publish(name, data)
			self._emit_status("publish", None)
			return True
		except Exception as exc:
			self._last_err = str(exc)
			if self.logger:
				self.logger.warning("Ably publish failed: %s", exc)
			return False

	def is_connected(self) -> bool:
		try:
			if not self._ably:
				return False
			state = getattr(self._ably.connection, "state", None)
			return str(state).lower() == "connected"
		except Exception:
			return False

	def get_status(self) -> str:
		return "connected" if self.is_connected() else "disconnected"

	def last_error(self) -> Optional[str]:
		return self._last_err


