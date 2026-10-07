import random

from mpf.core.custom_code import CustomCode


class PowerShots(CustomCode):

    POWER_SHOTS = [
        ("s_left_vuk_active", "led_honda_double"),
        ("s_right_vuk_active", "led_balrog_double"),
        ("s_chunli_exit_active", "led_chunli_double"),
        ("s_left_orbit_rollerover_active", "led_blanka_double"),
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

    def on_load(self):
        self.active_fight = None
        self.active_targets = {}
        self.power_hits = 0

        # Listen for every fight starting.
        for fight in self.FIGHTS:
            self.machine.events.add_handler(
                f"{fight}_started",
                self.fight_started,
                fight=fight
            )

            # Clear randomized targets when the fight mode ends.
            self.machine.events.add_handler(
                f"mode_{fight}_stopped",
                self.fight_stopped,
                fight=fight
            )

        # Listen for every possible power-shot switch.
        for switch, light in self.POWER_SHOTS:
            self.machine.events.add_handler(
                switch,
                self.power_shot_hit,
                switch=switch
            )

    def fight_started(self, fight, **kwargs):
        # Pick exactly 3 unique targets from the pool.
        selected = random.sample(self.POWER_SHOTS, 3)

        self.active_fight = fight
        self.power_hits = 0

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

        # Tell YAML which three lights should flash.
        self.machine.events.post(
            "power_shots_selected",
            lights=[light for switch, light in selected],
            fight=fight
        )

    def power_shot_hit(self, switch, **kwargs):
        # No randomized power-shot sequence is active.
        if not self.active_fight:
            return

        # Only two randomized targets can be hit.
        # After that, the final-blow shot takes over.
        if self.power_hits >= 2:
            return

        # This switch wasn't randomly selected for this fight.
        if switch not in self.active_targets:
            return

        # Remove the target immediately.
        #
        # This prevents the same switch from scoring again.
        light = self.active_targets.pop(switch)

        self.power_hits += 1

        # Preserve the existing fight progression.
        self.machine.events.post(
            "power_move_event"
        )

        # Tell YAML exactly which randomly selected light was hit.
        self.machine.events.post(
            "power_shot_hit",
            switch=switch,
            light=light,
            fight=self.active_fight
        )

        # Two power shots have now been hit.
        if self.power_hits == 2:

            # Whatever selected target(s) remain are no longer active.
            remaining_lights = list(self.active_targets.values())

            self.machine.events.post(
                "power_shots_complete",
                fight=self.active_fight,
                lights=remaining_lights
            )

            # Prevent any further randomized power-shot hits.
            self.active_targets.clear()

    def fight_stopped(self, fight, **kwargs):
        # Only clear the state belonging to the active fight.
        if self.active_fight == fight:
            self.active_fight = None
            self.active_targets.clear()
            self.power_hits = 0