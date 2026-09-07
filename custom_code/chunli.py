import subprocess
from mpf.core.custom_code import CustomCode

class Chunli(CustomCode):

    def on_load(self):
        """Initializes a single, parameter-flexible event handler."""
        # This listens for 'set_tic_velocity' and expects a 'velocity' argument
        self.machine.events.add_handler('set_tic_velocity', self.change_velocity)

    def change_velocity(self, velocity=0, **kwargs):
        """Dispatches the speed setting directly to the Pololu Tic hardware.
        
        Args:
            velocity: Target speed in microsteps per 10,000 seconds.
                      Defaults to 0 (stop) if missing.
        """
        del kwargs
        try:
            # Execute command line call to the local Pololu Tic utility
            subprocess.Popen(['ticcmd', '--velocity', str(int(velocity))], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
            
            if int(velocity) == 0:
                self.machine.log.info("Pololu Tic motor commanded to STOP.")
            else:
                self.machine.log.info(f"Pololu Tic velocity successfully adjusted to: {velocity}")
                
        except ValueError:
            self.machine.log.error(f"Invalid velocity format received: {velocity}")
        except Exception as e:
            self.machine.log.error(f"Failed to transmit data to Pololu Tic: {e}")

