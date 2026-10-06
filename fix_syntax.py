with open('src/brandly_cli/cmd/production.py') as f:
    content = f.read()

old = """            console.print(
                f"[yellow]  Proposed {schedule['days']}-day schedule: "
                f"{', '.join(f'Day {i+1}: {s}s ({schedule[\\\"shots_per_day\\\"][i]} shots)' "
                f"for i, s in enumerate(schedule['seconds_per_day']))}[/yellow]"
            )"""

new = """            day_strs = []
            for i, s in enumerate(schedule["seconds_per_day"]):
                shots = schedule["shots_per_day"][i]
                day_strs.append(f"Day {i+1}: {s}s ({shots} shots)")
            console.print(
                f"[yellow]  Proposed {schedule['days']}-day schedule: {', '.join(day_strs)}[/yellow]"
            )"""

content = content.replace(old, new)
open('src/brandly_cli/cmd/production.py', 'w').write(content)
print('done')