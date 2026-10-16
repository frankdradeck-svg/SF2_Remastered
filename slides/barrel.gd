
extends AnimatedSprite2D

enum State {
    ROLLING_TO_OPENING,
    FALLING_TO_BAR,
    BAR_BOUNCE,
    FALLING_TO_GROUND,
    GROUND_BOUNCE,
    ROLLING_OFFSCREEN
}

@export_group("Horizontal Movement")
@export var roll_speed: float = 180.0
@export var opening_x: float = 640.0

@export_group("Vertical Positions")
@export var bar_y: float = 350.0
@export var ground_y: float = 600.0

@export_group("Bounce Settings")
@export var bar_bounce_height: float = 65.0
@export var bar_bounce_duration: float = 0.45
@export var ground_bounce_height: float = 35.0
@export var ground_bounce_duration: float = 0.35

var state: State = State.ROLLING_TO_OPENING
var direction: float = 1.0

var arc_time: float = 0.0
var arc_duration: float = 0.0
var arc_start_y: float = 0.0
var arc_end_y: float = 0.0
var arc_height: float = 0.0


func _ready() -> void:
    play("barrel_roll_right")


func _process(delta: float) -> void:
    position.x += roll_speed * direction * delta

    match state:
        State.ROLLING_TO_OPENING:
            if direction > 0.0 and position.x >= opening_x:
                state = State.FALLING_TO_BAR
                _start_arc(position.y, bar_y, 0.45, 0.0)

            elif direction < 0.0 and position.x <= opening_x:
                state = State.FALLING_TO_BAR
                _start_arc(position.y, bar_y, 0.45, 0.0)

        State.FALLING_TO_BAR:
            if _update_arc(delta):
                state = State.BAR_BOUNCE
                _start_arc(bar_y, bar_y, bar_bounce_duration,
                        bar_bounce_height)

        State.BAR_BOUNCE:
            if _update_arc(delta):
                state = State.FALLING_TO_GROUND
                _start_arc(bar_y, ground_y, 0.55, 0.0)

        State.FALLING_TO_GROUND:
            if _update_arc(delta):
                state = State.GROUND_BOUNCE
                _start_arc(ground_y, ground_y,
                        ground_bounce_duration, ground_bounce_height)

        State.GROUND_BOUNCE:
            if _update_arc(delta):
                state = State.ROLLING_OFFSCREEN
                position.y = ground_y

        State.ROLLING_OFFSCREEN:
            if position.x < -100.0 or position.x > 2000.0:
                queue_free()


func _start_arc(
        start_y: float,
        end_y: float,
        duration: float,
        height: float
) -> void:
    arc_time = 0.0
    arc_duration = duration
    arc_start_y = start_y
    arc_end_y = end_y
    arc_height = height


func _update_arc(delta: float) -> bool:
    arc_time += delta
    var t: float = clampf(arc_time / arc_duration, 0.0, 1.0)

    # Smooth transition between the starting and ending heights.
    var base_y: float = lerpf(arc_start_y, arc_end_y, t)

    # A rounded arc: zero offset at both ends, maximum height in the middle.
    position.y = base_y - 4.0 * arc_height * t * (1.0 - t)

    return t >= 1.0
