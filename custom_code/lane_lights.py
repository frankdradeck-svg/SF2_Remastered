
from mpf.core.custom_code import CustomCode


class LaneLights(CustomCode):

    # Positions are ordered from left to right.
    LANES = [
        ("s_left_outlane", "led_left_outlane"),
        ("s_left_inlane", "led_left_inlane"),
        ("s_right_inlane", "led_right_inlane"),
        ("s_right_outlane", "led_right_outlane"),
    ]

    def on_load(self):
        # True means the position is currently completed.
        self.lane_states = [False] * len(self.LANES)
        self.completion_posted = False

        # Lane switches.
        for index, (switch_name, _) in enumerate(self.LANES):
            self.machine.events.add_handler(
                f"{switch_name}_active",
                lambda lane=index, **kwargs: self._lane_hit(lane)
            )

        # Flipper buttons rotate the entire row of statuses.
        self.machine.events.add_handler(
            "s_left_flipper_active", self._shift_left
        )
        self.machine.events.add_handler(
            "s_right_flipper_active", self._shift_right
        )

        # Reset automatically for every new ball.
        self.machine.events.add_handler(
            "ball_starting", self._reset
        )

        # Also allow any mode to request a reset.
        self.machine.events.add_handler(
            "lane_lights_reset", self._reset
        )

        # Start with every light off.
        self._update_lights()

    def _lane_hit(self, lane):
        # A completed position stays completed until shifted or reset.
        if self.lane_states[lane]:
            return

        self.lane_states[lane] = True
        self._update_lights()

        # Post completion only once per set.
        if all(self.lane_states) and not self.completion_posted:
            self.completion_posted = True
            self.machine.events.post("lane_lights_complete")

    def _shift_left(self, **kwargs):
        # The leftmost status wraps around to the right.
        self.lane_states = self.lane_states[1:] + self.lane_states[:1]
        self._update_lights()

    def _shift_right(self, **kwargs):
        # The rightmost status wraps around to the left.
        self.lane_states = self.lane_states[-1:] + self.lane_states[:-1]
        self._update_lights()

    def _reset(self, **kwargs):
        self.lane_states = [False] * len(self.LANES)
        self.completion_posted = False
        self._update_lights()

    def _update_lights(self):
        for completed, (_, light_name) in zip(
            self.lane_states, self.LANES
        ):
            light = self.machine.lights[light_name]

            if completed:
                light.on()
            else:
                light.off()
