
extends AnimatedSprite2D

enum State { IDLE, KICKING }

var state: State = State.IDLE
var facing_right: bool = false


func _ready() -> void:
    play("ryu_left")
    animation_finished.connect(_on_animation_finished)


func _input(event: InputEvent) -> void:
    if state == State.KICKING:
        return

    if event.is_action_pressed("ui_left"):
        kick_left()
    elif event.is_action_pressed("ui_right"):
        kick_right()


func kick_left() -> void:
    _start_kick(false)


func kick_right() -> void:
    _start_kick(true)


func _start_kick(to_right: bool) -> void:
    state = State.KICKING
    facing_right = to_right
    flip_h = facing_right
    play("ryu_kick")


func _on_animation_finished() -> void:
    if state != State.KICKING:
        return

    state = State.IDLE
    flip_h = facing_right
    play("ryu_left")
