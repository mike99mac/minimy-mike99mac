from framework.util.utils import execute_command

res = execute_command("amixer sget Master")
res = res.split("\n")

for line in res:
    if line.find("Limits") == -1:
        start_indx = line.find("Playback ")
        if start_indx > -1:
            line = line[start_indx + len("Playback "):]
            start_indx = line.find("[")
            if start_indx != -1:
                end_indx = line.find("]")
                current_volume = line[start_indx+1:end_indx].replace("%","")
                print(current_volume)

