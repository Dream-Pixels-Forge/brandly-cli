import asyncio
import inspect

print(inspect.signature(asyncio.run))
print()
print("Annotations:", asyncio.run.__annotations__)
