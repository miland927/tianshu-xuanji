"""上游熔断：连续失败就停手，冷却后再放一个探针进来。

三态：closed（正常）→ open（停手）→ half_open（放一个探针）→ 成功回 closed / 失败回 open。

为什么需要它：上游挂了的时候，每个请求都会等超时再降级——用户等，配额也照烧。
熔断让「已经知道坏了」这件事只付一次代价。

时钟可注入，测试里不用真的等 60 秒。
"""
from __future__ import annotations

import threading
import time

DEFAULT_THRESHOLD = 3
DEFAULT_COOLDOWN = 60.0


class Breaker:
    def __init__(self, threshold: int = DEFAULT_THRESHOLD, cooldown: float = DEFAULT_COOLDOWN,
                 clock=time.monotonic):
        self.threshold = threshold
        self.cooldown = cooldown
        self._clock = clock
        self._lock = threading.Lock()
        self.state = 'closed'
        self.failures = 0
        self.opened_at = 0.0
        self.probing = False

    def allow(self) -> bool:
        """能不能打上游。open 且冷却已过 → 转 half_open 并放一个探针。"""
        with self._lock:
            if self.state == 'closed':
                return True
            if self.state == 'open':
                if self._clock() - self.opened_at >= self.cooldown:
                    self.state = 'half_open'
                    self.probing = True
                    return True
                return False
            # half_open：只放一个探针
            if self.probing:
                return False
            self.probing = True
            return True

    def success(self) -> None:
        with self._lock:
            self.state = 'closed'
            self.failures = 0
            self.opened_at = 0.0
            self.probing = False

    def failure(self) -> None:
        with self._lock:
            if self.state == 'half_open':
                self.state = 'open'
                self.opened_at = self._clock()
                self.probing = False
                return
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = 'open'
                self.opened_at = self._clock()
                self.probing = False

    def snapshot(self) -> dict:
        with self._lock:
            left = 0.0
            if self.state == 'open':
                left = max(0.0, self.cooldown - (self._clock() - self.opened_at))
            return {'state': self.state, 'failures': self.failures,
                    'threshold': self.threshold, 'cooldown_s': self.cooldown,
                    'retry_in_s': round(left, 1)}

    def reset(self) -> None:
        with self._lock:
            self.state = 'closed'
            self.failures = 0
            self.opened_at = 0.0
            self.probing = False


#: 进程里共用一只
BREAKER = Breaker()
