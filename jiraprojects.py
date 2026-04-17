from jira import JIRA
import os
from dotenv import load_dotenv

load_dotenv()
j = JIRA(server=os.environ['JIRA_SERVER'], basic_auth=(os.environ['JIRA_EMAIL'], os.environ['JIRA_API_TOKEN']))
print('=== PROYECTOS ===')
for p in j.projects():
    print(p.key, '-', p.name)
print()
print('=== CAMPOS DISPONIBLES ===')
for f in j.fields():
    print(f['id'], '-', f['name'])