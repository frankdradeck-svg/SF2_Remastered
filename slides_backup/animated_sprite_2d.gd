
extends AnimatedSprite2D

enum State { IDLE, KICKING }

var state: State = State.IDLE
var facing_right: bool = false
var hit_barrels: Array[Node] = []

@export_group("Kick Hit Detection")
@export var kick_range: float = 150.0
@export var hit_area_top: float = 100.0
@export var hit_area_bottom: float = 50.0
@export var kick_hit_delay: float = 0.18

@export_group("Kick Audio")
@export var kick_sound_delay: float = 0.0

@onready var kick_sound: AudioStreamPlayer = $KickSound

var kick_elapsed: float = 0.0
var kick_sound_played: bool = false


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


func _process(delta: float) -> void:
    if state != State.KICKING:
        return

    kick_elapsed += delta

    # Play the kick sound after its adjustable delay.
    if not kick_sound_played:
        if kick_elapsed >= kick_sound_delay:
            kick_sound.play()
            kick_sound_played = true

    # Check for barrel hits after the kick reaches the
    # configured point in its animation.
    if kick_elapsed >= kick_hit_delay:
        _check_for_barrel_hit()


func kick_left() -> void:
    _start_kick(false)


func kick_right() -> void:
    _start_kick(true)


func _start_kick(to_right: bool) -> void:
    state = State.KICKING
    facing_right = to_right
    hit_barrels.clear()
    kick_elapsed = 0.0
    kick_sound_played = false

    flip_h = facing_right
    play("ryu_kick")


func _check_for_barrel_hit() -> void:
    var barrels = get_tree().get_nodes_in_group("barrels")

    for barrel in barrels:
        if not is_instance_valid(barrel):
            continue

        if barrel in hit_barrels:
            continue

        if not barrel.can_be_hit():
            continue

        var horizontal_distance: float = (
            barrel.global_position.x - global_position.x
        )

        var vertical_distance: float = (
            barrel.global_position.y - global_position.y
        )

        if facing_right:
            if horizontal_distance <= 0.0:
                continue
        else:
            if horizontal_distance >= 0.0:
                continue

        if absf(horizontal_distance) > kick_range:
            continue

        if vertical_distance < -hit_area_top:
            continue

        if vertical_distance > hit_area_bottom:
            continue

        print("BARREL HIT!")
        hit_barrels.append(barrel)
        barrel.hit()


func _on_animation_finished() -> void:
    if state != State.KICKING:
        return

    state = State.IDLE
    flip_h = facing_right
    play("ryu_left")
