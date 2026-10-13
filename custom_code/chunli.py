import random
import subprocess

from mpf.core.custom_code import CustomCode


class ChunLi(CustomCode):

    TIC_SERIAL = "00506424"

    # ---------------------------------------------------------------
    # MOTION SETTINGS
    # ---------------------------------------------------------------

    # Speed used for the final physical return to the home switch.
    HOME_SPEED = 900000

    # Speed used for the three intro/animation position moves.
    ANIMATION_SPEED = 5000000

    # Motion profile for position moves.
    MAX_SPEED = 5000000
    STARTING_SPEED = 3000000
    MAX_ACCEL = 5000000
    MAX_DECEL = 5000000

    # Full-step mode:
    #
    # 200 steps = 360 degrees
    # 50 steps  = 90 degrees
    # 20 steps  = 36 degrees
    #
    ANIMATION_FORWARD_STEPS = 50
    ANIMATION_REVERSE_STEPS = 20
    ANIMATION_FORWARD_AGAIN_STEPS = 20

    # Map current_player.chun_speed (0-100) to Tic velocity.
    MIN_DYNAMIC_VELOCITY = 1250000
    MAX_DYNAMIC_VELOCITY = 5000000
    DYNAMIC_SPEED_MIN = 0
    DYNAMIC_SPEED_MAX = 100

    # Tic command timeout is 1 second.
    HEARTBEAT_INTERVAL = 0.20

    # Small delay between position commands.
    MOVE_DELAY = 0.15

    def on_load(self):

        # -----------------------------------------------------------
        # STATE
        # -----------------------------------------------------------

        # Possible states:
        #
        #   idle
        #   homing
        #   moving_50
        #   moving_back_20
        #   moving_forward_20
        #   returning_home
        #
        self.state = "idle"

        # Tracks whether the mechanism is physically known to be home.
        self.at_home = True

        # Dynamic velocity updates are enabled only during
        # the chunli_fighter mode.
        self.velocity_updates_enabled = False
        self.last_velocity = None

        # -----------------------------------------------------------
        # MPF EVENTS
        # -----------------------------------------------------------

        self.machine.events.add_handler(
            "chunli_intro_start",
            self.intro_start
        )

        self.machine.events.add_handler(
            "chunli_home",
            self.home
        )

        self.machine.events.add_handler(
            "chunli_move_90",
            self.move_90
        )

        # Enable dynamic velocity updates only during chunli_fighter.
        self.machine.events.add_handler(
            "mode_chunli_fighter_started",
            self._enable_velocity_updates
        )

        self.machine.events.add_handler(
            "mode_chunli_fighter_stopped",
            self._disable_velocity_updates
        )

        # -----------------------------------------------------------
        # HEARTBEAT
        # -----------------------------------------------------------

        self.machine.clock.schedule_interval(
            self._heartbeat,
            self.HEARTBEAT_INTERVAL
        )

        self.log.info(
            "ChunLi custom code loaded."
        )

    # ---------------------------------------------------------------
    # TIC COMMAND
    # ---------------------------------------------------------------

    def _ticcmd(self, *args):
        """Send a command to the Pololu Tic."""

        command = [
            "ticcmd",
            "-d",
            self.TIC_SERIAL,
            *args
        ]

        try:

            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            return True

        except subprocess.CalledProcessError:

            self.log.warning(
                "Tic command failed: %s",
                " ".join(command)
            )

            return False

    # ---------------------------------------------------------------
    # HEARTBEAT
    # ---------------------------------------------------------------

    def _heartbeat(self):
        """Keep the Tic alive and update velocity during chunli_fighter."""

        # Preserve the existing Tic heartbeat.
        self._ticcmd("--reset-command-timeout")

        # Do not read the player variable outside chunli_fighter mode.
        if not self.velocity_updates_enabled:
            return

        player = self.machine.game.player

        if player is None:
            return

        # Keep the MPF gameplay value within its intended 0-100 range.
        chun_speed = int(player.chun_speed)
        chun_speed = max(
            self.DYNAMIC_SPEED_MIN,
            min(self.DYNAMIC_SPEED_MAX, chun_speed)
        )

        # Linear mapping:
        # 0   -> 1,250,000
        # 100 -> 5,000,000
        velocity_range = (
            self.MAX_DYNAMIC_VELOCITY - self.MIN_DYNAMIC_VELOCITY
        )
        speed_range = self.DYNAMIC_SPEED_MAX - self.DYNAMIC_SPEED_MIN

        velocity = self.MIN_DYNAMIC_VELOCITY + int(
            (chun_speed - self.DYNAMIC_SPEED_MIN)
            * velocity_range
            / speed_range
        )

        # Avoid sending the same velocity repeatedly.
        if velocity == self.last_velocity:
            return

        if self._ticcmd("--velocity", str(velocity)):
            self.last_velocity = velocity
            self.log.debug(
                "ChunLi dynamic velocity: chun_speed=%d, velocity=%d.",
                chun_speed,
                velocity
            )

    def _enable_velocity_updates(self, **kwargs):
        """Enable dynamic velocity updates when chunli_fighter starts."""

        self.velocity_updates_enabled = True
        self.last_velocity = None

        self.log.info("ChunLi fighter velocity updates enabled.")

    def _disable_velocity_updates(self, **kwargs):
        """Disable dynamic velocity updates when chunli_fighter stops."""

        self.velocity_updates_enabled = False
        self.last_velocity = None

        self.log.info("ChunLi fighter velocity updates disabled.")

    # ---------------------------------------------------------------
    # MODE START
    # ---------------------------------------------------------------

    def intro_start(self, **kwargs):
        """
        Reset the Tic and begin automatic homing.
        """

        self.log.info(
            "ChunLi intro starting."
        )

        self.state = "homing"
        self.at_home = False

        # Reset the Tic.
        self._ticcmd(
            "--reset"
        )

        # Start homing shortly after reset.
        self.machine.clock.schedule_once(
            self._start_homing,
            0.05
        )

    # ---------------------------------------------------------------
    # START HOMING
    # ---------------------------------------------------------------

    def _start_homing(self):
        """
        Start continuous movement toward the physical home switch.
        """

        self._ticcmd(
            "--max-speed",
            str(self.MAX_SPEED)
        )

        self._ticcmd(
            "--starting-speed",
            str(self.STARTING_SPEED)
        )

        self._ticcmd(
            "--max-accel",
            str(self.MAX_ACCEL)
        )

        self._ticcmd(
            "--max-decel",
            str(self.MAX_DECEL)
        )

        # Exit safe start.
        self._ticcmd(
            "--resume"
        )

        # Initial homing is deliberately slower.
        self._ticcmd(
            "--velocity",
            str(self.HOME_SPEED)
        )

        self.log.info(
            "ChunLi homing motion started at %d.",
            self.HOME_SPEED
        )

    # ---------------------------------------------------------------
    # HOME SWITCH
    # ---------------------------------------------------------------

    def home(self, **kwargs):
        """
        Physical home switch activated.

        Used for both initial homing and the final return
        at the end of the entrance animation.
        """

        # -----------------------------------------------------------
        # INITIAL HOMING
        # -----------------------------------------------------------

        if self.state == "homing":

            self.log.info(
                "ChunLi home switch activated during startup homing."
            )

            self._ticcmd(
                "--halt-and-set-position",
                "0"
            )

            self.state = "idle"
            self.at_home = True

            self.log.info(
                "ChunLi homed. Position = 0."
            )

            return

        # -----------------------------------------------------------
        # RETURNING HOME
        # -----------------------------------------------------------

        if self.state == "returning_home":

            self.log.info(
                "ChunLi home switch activated during animation."
            )

            self._ticcmd(
                "--halt-and-set-position",
                "0"
            )

            self.state = "idle"
            self.at_home = True

            self.log.info(
                "ChunLi returned home. Position reset to 0."
            )

            return

    # ---------------------------------------------------------------
    # ENTRANCE SWITCH
    # ---------------------------------------------------------------

    def move_90(self, **kwargs):
        """
        Entrance switch behavior.

        Every other trigger is ignored.

        Active trigger runs:

            +50 steps
            -20 steps
            +20 steps
            continuous reverse until home switch
        """

        # -----------------------------------------------------------
        # IGNORE DURING HOMING
        # -----------------------------------------------------------

        if self.state == "homing":
            return

        # -----------------------------------------------------------
        # IGNORE TRIGGERS WHILE ANIMATION IS RUNNING
        # -----------------------------------------------------------

        if self.state != "idle":
            return

        # -----------------------------------------------------------
        # RANDOMLY RUN THE ANIMATION OR IGNORE THIS TRIGGER
        # -----------------------------------------------------------

        # Each entrance trigger gets an independent 50/50 decision;
        # unlike the previous toggle, this can randomly select the
        # animation on consecutive triggers or skip several in a row.
        if random.choice((True, False)):

            self.log.info(
                "ChunLi entrance trigger: randomly selected; starting animation."
            )

            self.start_animation()

        else:

            self.log.info(
                "ChunLi entrance trigger: randomly selected; animation skipped."
            )

    # ---------------------------------------------------------------
    # START ANIMATION
    # ---------------------------------------------------------------

    def start_animation(self):
        """
        Start:

            +50 steps
        """

        if self.state != "idle":
            return

        self.state = "moving_50"
        self.at_home = False

        success = self._ticcmd(
            "--position-relative",
            str(self.ANIMATION_FORWARD_STEPS)
        )

        if not success:

            self.state = "idle"

            self.log.warning(
                "ChunLi +50 movement failed."
            )

            return

        self.log.info(
            "ChunLi animation: +50 steps."
        )

        # Tell MPF that the ChunLi animation actually started.
        self.machine.events.post("chunli_animation_started")

        # Give the Tic time to complete the move.
        self.machine.clock.schedule_once(
            self._animation_reverse_20,
            self.MOVE_DELAY
        )

    # ---------------------------------------------------------------
    # ANIMATION: REVERSE 20
    # ---------------------------------------------------------------

    def _animation_reverse_20(self):
        """
        Move:

            -20 steps
        """

        if self.state != "moving_50":
            return

        self.state = "moving_back_20"

        success = self._ticcmd(
            "--position-relative",
            str(-self.ANIMATION_REVERSE_STEPS)
        )

        if not success:

            self.state = "idle"

            self.log.warning(
                "ChunLi animation -20 movement failed."
            )

            return

        self.log.info(
            "ChunLi animation: -20 steps."
        )

        self.machine.clock.schedule_once(
            self._animation_forward_20,
            self.MOVE_DELAY
        )

    # ---------------------------------------------------------------
    # ANIMATION: FORWARD 20
    # ---------------------------------------------------------------

    def _animation_forward_20(self):
        """
        Move:

            +20 steps
        """

        if self.state != "moving_back_20":
            return

        self.state = "moving_forward_20"

        success = self._ticcmd(
            "--position-relative",
            str(self.ANIMATION_FORWARD_AGAIN_STEPS)
        )

        if not success:

            self.state = "idle"

            self.log.warning(
                "ChunLi animation +20 movement failed."
            )

            return

        self.log.info(
            "ChunLi animation: +20 steps."
        )

        # After the +20 finishes, begin the slow continuous
        # return toward the physical home switch.
        self.machine.clock.schedule_once(
            self._start_animation_return,
            self.MOVE_DELAY
        )

    # ---------------------------------------------------------------
    # ANIMATION: RETURN HOME
    # ---------------------------------------------------------------

    def _start_animation_return(self):
        """
        Continuously move backward at 900,000 until the physical
        home switch activates.
        """

        if self.state != "moving_forward_20":
            return

        self.state = "returning_home"

        success = self._ticcmd(
            "--velocity",
            str(-self.HOME_SPEED)
        )

        if not success:

            self.state = "idle"

            self.log.warning(
                "ChunLi animation return-home command failed."
            )

            return

        self.log.info(
            "ChunLi animation: returning home at %d.",
            self.HOME_SPEED
        )
