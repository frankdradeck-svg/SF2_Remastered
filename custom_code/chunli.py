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

        # Every other entrance trigger does nothing.
        #
        # True  = next entrance trigger runs the animation
        # False = next entrance trigger does nothing
        #
        self.animation_enabled = True

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
        """Keep the Tic command timeout alive."""

        self._ticcmd(
            "--reset-command-timeout"
        )

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
        # ALTERNATE BETWEEN ANIMATION AND DO NOTHING
        # -----------------------------------------------------------

        if not self.animation_enabled:

            self.log.info(
                "ChunLi entrance trigger ignored."
            )

            # Next trigger will run the animation.
            self.animation_enabled = True

            return

        # This trigger runs the animation.
        self.animation_enabled = False

        self.log.info(
            "ChunLi entrance trigger: starting animation."
        )

        self.start_animation()

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
