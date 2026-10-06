"""Четыре шага движения при постоянном ускорении."""
from solar_simulator.motion import update_position, update_velocity


def main():
    position, velocity = 10.0, 3.0
    for step in range(4):
        position = update_position(position, velocity, -2.0, 0.5)
        velocity = update_velocity(velocity, -2.0, 0.5)
        print(f"Step {step + 1}: x={position} m, v={velocity} m/s")


if __name__ == "__main__":
    main()
