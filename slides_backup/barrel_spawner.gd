
extends Node2D

@export_group("Barrel Scene")
@export var barrel_scene: PackedScene

@export_group("Spawn Timing")
@export var spawn_cutoff: float = 28.0
@export var min_spawn_interval: float = 0.7
@export var max_spawn_interval: float = 1.5
@export var max_active_barrels: int = 3

@export_group("Spawn Positions")
@export var left_spawn_x: float = -80.0
@export var right_spawn_x: float = 2000
@export var spawn_y: float = 20

var elapsed: float = 0.0
var time_until_spawn: float = 0.0
var spawn_from_left: bool = true
var active_barrels: Array[Node] = []


func _ready() -> void:
    randomize()
    time_until_spawn = 0.0


func _process(delta: float) -> void:
    elapsed += delta

    # Remove references to barrels that have left the scene.
    active_barrels = active_barrels.filter(
        func(barrel): return is_instance_valid(barrel)
    )

    # Stop spawning at the configured cutoff.
    if elapsed >= spawn_cutoff:
        return

    time_until_spawn -= delta

    if time_until_spawn <= 0.0:
        if active_barrels.size() < max_active_barrels:
            _spawn_barrel()

        time_until_spawn = randf_range(
            min_spawn_interval,
            max_spawn_interval
        )


func _spawn_barrel() -> void:
    if barrel_scene == null:
        push_error("BarrelSpawner: Assign barrel_scene in the Inspector.")
        return

    var barrel: Node = barrel_scene.instantiate()

    # Alternate direction on every successful spawn.
    var direction: float = 1.0 if spawn_from_left else -1.0

    barrel.set("direction", direction)
    barrel.position = Vector2(
        left_spawn_x if spawn_from_left else right_spawn_x,
        spawn_y
    )
    print("Spawner Spawn Y: ", spawn_y)
    print("New barrel position: ", barrel.position)

    # Add it to Fight, not to the spawner, so its position
    # and movement use the main scene's coordinates.
    get_parent().add_child(barrel)
    active_barrels.append(barrel)

    spawn_from_left = not spawn_from_left
