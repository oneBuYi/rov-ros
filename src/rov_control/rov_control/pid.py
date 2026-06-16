import time


class PID:
    def __init__(self, kp, ki, kd, out_min, out_max):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.out_min = out_min
        self.out_max = out_max
        self.reset()

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None

    def update(self, setpoint, measurement):
        error = setpoint - measurement
        now = time.time()
        if self._prev_time is None:
            self._prev_error = error
            self._prev_time = now
            return 0.0

        dt = now - self._prev_time
        if dt <= 0:
            return 0.0

        p_term = self.kp * error
        self._integral += self.ki * (error + self._prev_error) * dt / 2.0
        if self._integral > self.out_max:
            self._integral = self.out_max
        elif self._integral < self.out_min:
            self._integral = self.out_min

        d_term = self.kd * (error - self._prev_error) / dt
        output = p_term + self._integral + d_term

        if output > self.out_max:
            output = self.out_max
        elif output < self.out_min:
            output = self.out_min

        self._prev_error = error
        self._prev_time = now
        return output
