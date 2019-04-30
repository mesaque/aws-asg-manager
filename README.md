# aws-asg-manager

My scenario:

- A WordPress configured in a EC2 called "MODEL" or "ADMIN" and i want that every time my project get updated all of ASG spawned servers starts with the updated project too!!


so this is a lambda function that generate a snapshot from my ADMIN machine and make an AMI , copy the LC and change his image base after that it changes the LC on ASG.
