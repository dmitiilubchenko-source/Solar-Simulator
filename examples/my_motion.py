import numpy as np
import matplotlib.pyplot as plt

from src.motion import calculate_position

times = np.linspace(0.0, 10.0, 11)
position = calculate_position(
    initial_position= 5.0,
    velocity= 3.0,
    time = times,
)

plt.plot(times, position)
plt.xlabel("Время,с")
plt.ylabel("Координата,м")
plt.title("Равномерное движение")
plt.grid()
plt.show()
print(times)
print(position)
