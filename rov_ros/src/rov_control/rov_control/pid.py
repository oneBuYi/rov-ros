"""离散 PID 控制器，带积分抗饱和。

从原 alg/pid.py 迁移。纯 Python 模块，无 ROS 依赖。
"""

import time


class PID:
    """离散 PID 控制器。

    error = setpoint - measurement（正作用）
    积分项使用梯形积分，在输出域钳位抗饱和。
    微分项直接对误差求导。

    Usage:
        pid = PID(kp=100, ki=40, kd=80, out_min=-100, out_max=100)
        output = pid.update(setpoint=0.5, measurement=0.3)
        pid.reset()
    """

    def __init__(self, kp, ki, kd, out_min, out_max):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.out_min = float(out_min)
        self.out_max = float(out_max)

        self._integral = 0.0
        self._prev_error = None
        self._prev_time = None

    def update(self, setpoint, measurement):
        """计算 PID 输出。

        Args:
            setpoint: 目标值
            measurement: 当前测量值

        Returns:
            float: 控制输出，范围 [out_min, out_max]
        """
        error = setpoint - measurement  # 正作用
        now = time.time()

        if self._prev_time is None:
            self._prev_error = error
            self._prev_time = now
            return 0.0

        dt = now - self._prev_time
        if dt <= 0:
            return 0.0

        # 比例项
        p_term = self.kp * error

        # 积分项（梯形积分）
        self._integral += self.ki * (error + self._prev_error) * dt / 2.0

        # 输出域钳位抗饱和：积分项被限制在 [out_min, out_max]
        if self._integral > self.out_max:
            self._integral = self.out_max
        elif self._integral < self.out_min:
            self._integral = self.out_min

        i_term = self._integral

        # 微分项（直接对误差求导）
        d_term = self.kd * (error - self._prev_error) / dt

        output = p_term + i_term + d_term

        # 输出钳位
        if output > self.out_max:
            output = self.out_max
        elif output < self.out_min:
            output = self.out_min

        self._prev_error = error
        self._prev_time = now

        return output

    def reset(self):
        """清除积分和微分状态。"""
        self._integral = 0.0
        self._prev_error = None
        self._prev_time = None
