import os
import schedule
import time
from datetime import datetime



def git_push():
    try:
        # Navigate to the repository directory
        repo_path = "/home/msk/git/Url-Shortner"  # Replace with your repository path
        os.chdir(repo_path)

        # Check if there are any changes
        status = os.popen("git status --porcelain").read().strip()
        if not status:
            print("No changes detected. Skipping commit and push.")
            return

        # Git commands
        os.system("git add .")
        os.system('git commit -m "Auto-commit on {}"'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        os.system("git push origin main")  # Replace "main" with your branch name if different

        print("Changes pushed to GitHub successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")

# Schedule the task to run every 24 hours
#schedule.every(24).hours.do(git_push)

# Run the scheduler
# while True:
#     schedule.run_pending()
#     time.sleep(1)
git_push()