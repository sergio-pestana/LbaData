"""Cliente HTTP para a API pública (não documentada oficialmente) do go-champs.

Sequencial, com intervalo mínimo entre requisições e checagem de robots.txt —
Princípio II da constituição (coleta respeitosa).
"""

from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Any

import requests

USER_AGENT = "LBA-POA-Data-Collector/0.1 (uso pessoal, projeto de analytics; contato: serg.poa@gmail.com)"


class RobotsDisallowedError(RuntimeError):
    """Levantado quando o robots.txt da fonte proíbe a coleta do path pedido."""


@dataclass
class GoChampsClient:
    base_url: str = "https://api.go-champs.com"
    user_agent: str = USER_AGENT
    min_interval_seconds: float = 1.5
    _last_request_at: float = field(default=0.0, init=False, repr=False)
    _robots_parser: urllib.robotparser.RobotFileParser | None = field(default=None, init=False, repr=False)

    def _load_robots(self) -> urllib.robotparser.RobotFileParser:
        """Busca o robots.txt com nosso próprio User-Agent identificável.

        Não usamos RobotFileParser.read() diretamente: ele faz sua própria
        requisição HTTP com o User-Agent padrão do urllib, e o WAF do host
        bloqueia esse UA genérico com 403 — o que faria o parser concluir
        (de forma incorreta) que tudo está desautorizado. Buscamos o texto nós
        mesmos, com o mesmo UA que usamos para os dados, e alimentamos o parser.
        """
        if self._robots_parser is not None:
            return self._robots_parser

        parser = urllib.robotparser.RobotFileParser()
        robots_url = f"{self.base_url}/robots.txt"
        try:
            response = requests.get(
                robots_url,
                headers={"User-Agent": self.user_agent},
                timeout=10,
            )
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                # robots.txt inacessível: postura conservadora, mas não silenciosa.
                parser.disallow_all = True
        except requests.RequestException:
            parser.disallow_all = True

        self._robots_parser = parser
        return parser

    def _check_allowed(self, path: str) -> None:
        parser = self._load_robots()
        url = f"{self.base_url}{path}"
        if not parser.can_fetch(self.user_agent, url):
            raise RobotsDisallowedError(
                f"robots.txt de {self.base_url} não permite coletar {path} "
                f"para o User-Agent '{self.user_agent}'"
            )

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = self.min_interval_seconds - elapsed
        if wait > 0:
            time.sleep(wait)

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET sequencial e respeitoso: valida robots.txt, aplica intervalo mínimo,
        envia User-Agent identificável, e retorna o JSON decodificado.
        """
        self._check_allowed(path)
        self._throttle()

        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            headers={"User-Agent": self.user_agent},
            timeout=30,
        )
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response.json()
