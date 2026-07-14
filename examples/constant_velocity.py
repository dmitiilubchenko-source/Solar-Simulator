import numpy as np
import matplotlib.pyplot as plt
from src.motion import calculate_position


times = np.linspace(0.0, 10.0, 21)
positions = calculate_position(
    initial_position=50.0,
    velocity=-4.0,
    time=times,
)

plt.plot(times, positions)
plt.xlabel("Время, с")
plt.ylabel("Координата, м")
plt.title("Равномерное движение, м/c")
plt.grid()
plt.show()

print(times)
print(positions)
