

def calculate_position(
    initial_position:float,
    velocity:float,
    time:float,
)->float:
    return initial_position + velocity * time
"""Формула x=x0 ​+ vt"""
result = calculate_position(10, 3, 4)
print(result)
