import random
import time

from mpf.core.custom_code import CustomCode


class PowerShots(CustomCode):

    POWER_SHOTS = [
        ("s_left_vuk_active", "led_honda_double"),
        ("s_right_vuk_active", "led_balrog_double"),
        ("s_chunli_exit_active", "led_chunli_double"),
        ("s_left_orbit_rollover_active", "led_blanka_double"),
        ("spinner_center_spinner_active", "led_dhalsim_double"),
        ("s_zangief_active", "led_zangief_double"),
        ("s_guile_opto_active", "led_guile_double"),
        ("spinner_loop_spinner_active", "led_ryu_double"),
    ]

    FIGHTS = (
        "vega",
        "chunli",
        "blanka",
        "zangief",
        "balrog",
        "ehonda",
        "sagat",
        "dhalsim",
    )

    # Ignore power-shot hits during the fight's opening seconds.
    HIT_PROTECTION_SECONDS = 3

    def on_load(self):
        self.active_fight = None
        self.active_targets = {}
        self.power_hits = 0
        self.fight_started_at = 0

        # Register handlers for fight start and stop events.
        for fight in self.FIGHTS:
            self.machine.events.add_handler(
                f"mode_{fight}_started",
                self.fight_started,
                fight=fight
            )

            self.machine.events.add_handler(
                f"mode_{fight}_stopped",
                self.fight_stopped,
                fight=fight
            )

        # Register handlers for all randomized shot switches.
        for switch, light in self.POWER_SHOTS:
            self.machine.events.add_handler(
                switch,
                self.power_shot_hit,
                switch=switch
            )

    def fight_started(self, fight, **kwargs):
        # Record the start time so early switch activations are ignored.
        self.active_fight = fight
        self.fight_started_at = time.monotonic()
        self.power_hits = 0

        # Randomly select three unique shot/light pairs.
        selected = random.sample(self.POWER_SHOTS, 3)

        self.active_targets = {
            switch: light
            for switch, light in selected
        }

        self.machine.log.info(
            "Power shots for %s: %s",
            fight,
            ", ".join(
                f"{switch} -> {light}"
                for switch, light in selected
            )
        )

        # Start a separate flash show for each selected light.
        for switch, light in selected:
            self.machine.events.post(
                f"power_shot_selected_{light}"
            )

            self.machine.log.info(
                "Started power-shot flash: %s -> %s",
                switch,
                light
            )

    def power_shot_hit(self, switch, **kwargs):
        # Ignore hits when no fight is active.
        if not self.active_fight:
            return

        # Ignore switch activations during the opening protection window.
        elapsed = time.monotonic() - self.fight_started_at

        if elapsed < self.HIT_PROTECTION_SECONDS:
            self.machine.log.debug(
                "Ignoring power-shot hit during opening protection: "
                "%s (%.2f seconds elapsed)",
                switch,
                elapsed
            )
            return

        # Only the first two randomized targets count.
        if self.power_hits >= 2:
            return

        # Ignore switches that weren't selected for this fight.
        if switch not in self.active_targets:
            return

        # Remove the target immediately to prevent duplicate hits.
        light = self.active_targets.pop(switch)

        self.power_hits += 1

        # Stop flashing this specific light.
        self.machine.events.post(
            f"power_shot_flash_stop_{light}"
        )

        # Preserve the existing fight progression.
        self.machine.events.post("power_move_event")

        # Tell YAML which selected light was hit.
        self.machine.events.post(
            "power_shot_hit",
            switch=switch,
            light=light,
            fight=self.active_fight
        )

        # After two valid hits, stop any unused selected flashes.
        if self.power_hits == 2:
            for remaining_light in self.active_targets.values():
                self.machine.events.post(
                    f"power_shot_flash_stop_{remaining_light}"
                )

                self.machine.events.post(
                    "power_shot_light_off",
                    light=remaining_light
                )

            self.machine.events.post(
                "power_shots_complete",
                fight=self.active_fight
            )

            # No further randomized shots count in this fight.
            self.active_targets.clear()

    def fight_stopped(self, fight, **kwargs):
        # Clear state only when the active fight stops.
        if self.active_fight == fight:
            # Stop all power-shot flashes to prevent lingering shows.
            for switch, light in self.POWER_SHOTS:
                self.machine.events.post(
                    f"power_shot_flash_stop_{light}"
                )

            self.active_fight = None
            self.active_targets.clear()
            self.power_hits = 0
            self.fight_started_at = 0
