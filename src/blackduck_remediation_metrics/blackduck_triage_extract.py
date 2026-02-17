# -*- coding: utf-8 -*-
'''
This script is used to export remediation status for given level.

By default the script is exporting the status for all projects in given
Black Duck instance. There are some filtering implemented to limit the 
project count.

Will need following: Python 3 and module: blackduck, jinja2, pdfkit and tinydb
To install the needed modules: 

pip install blackduck jinja2 pdfkit tinydb BetterJSONStorage
OR
pip install -r requirements.txt

Pdfkit requires that you have wkhtmltopdf installed and in your path. (https://wkhtmltopdf.org/)

This script is using template: BD_Results_Distribution_by_Triage_Status_v3.html. This template must be in templates -folder.

To get AccessToken, use your Internet browser and go to:
<BD_URL>/api/current-user/tokens?limit=100&offset=0
From there click "+ Create Token" -button and give the name and Scope: "Read and Write Access" and click "Create" -button.
Then copy&paste the given accesstoken. 
NOTE: After you click "Close" -button, you cannot see the token anymore.

Usage:
#To run HTML and PDF report for all projects in Black Duck -instance
python blackduck_triage_extract.py --token="<ACCESS_TOKEN>" --url="<BD_URL>" --html --pdf --json

#To generate interactive dashboard with charts and visualizations
python blackduck_triage_extract.py --token="<ACCESS_TOKEN>" --url="<BD_URL>" --dashboard --json

#To collect metrics for all projects in Black Duck by using the cache
python blackduck_triage_extract.py --token="<ACCESS_TOKEN>" --url="<BD_URL>" --cache --html --pdf --json

#To run HTML and PDF report for all projects in given project group. This will collect all projects from given project group and
#also all projects from sub project groups recursively.
python blackduck_triage_extract.py --token="<ACCESS_TOKEN>" --url="<BD_URL>" --project_group_name="<PROJECT_GROUP_NAME>" --html --pdf

#To run HTML and PDF report for given project and version
python blackduck_triage_extract.py --token="<ACCESS_TOKEN>" --url="<BD_URL>" --project="<PROJECT_NAME>" --version="<PROJECT_VERSION_NAME>" --html --pdf

#To limit projects based on project version phases DEVELOPMENT and PLANNING. Options are: PLANNING,DEVELOPMENT,RELEASED,DEPRECATED,ARCHIVED,PRERELEASE
python blackduck_triage_extract.py --token="<ACCESS_TOKEN>" --url="<BD_URL>" --phaseCategories="PLANNING,DEVELOPMENT" --html --pdf

#To limit projects based on project version distribution EXTERNAL and create only HTML report. Options are: EXTERNAL,SAAS,INTERNAL,OPENSOURCE
python blackduck_triage_extract.py --token="<ACCESS_TOKEN>" --url="<BD_URL>" --distributionCategories="EXTERNAL" --html

#By default all reports are written in the current folder where script is run, but if you want to change the folder, you can use --dir to give a new folder
python blackduck_triage_extract.py --token="<ACCESS_TOKEN>" --url="<BD_URL>" --dir="./reports" --html --pdf

If Proxy is needed, you can use export method.
#Example:
export HTTP_PROXY='http://10.10.10.10:8000'
export HTTPS_PROXY='https://10.10.10.10:1212'

NOTE: You can set token and url parameters as an environment variable:
export BD_TOKEN="<BD_TOKEN>"
export BD_URL="<BD_URL>"

Version History:
0.1.5 - Added usage of TinyDB (https://tinydb.readthedocs.io/en/latest/index.html) for caching BD metrics.
0.1.6 - Added triangle icon in front of project version, if project version last scanning date is older than given threshold (--sinceDays). Default is 30 days.
      - Added Last scanned -date for project versions
0.1.7 - Change to use BetterJSONStorage to improve performance and reduce the database size.
0.1.8 - Added check if project has updated compared last run project.updatedAt has changed, if it has the project info will be updated into cache.
0.1.9 - Added feature to export report as in JSON -format by adding --json.
0.1.10 - Added progressbar by using tqdm to show progress of projects analysis phases
0.1.11 - Added NOT_AFFECTED remediation type and removed BetterJSONStorage usage
0.1.12 - Fixed issues where there might be vulnerabilities without severity
0.1.13 - Added missing remediation statuses UNDER_INVESTIGATION and AFFECTED
0.1.14 - Fixed issue where key word snippetScanPresent was missing
0.1.15 - Fixed issue where totalCount key was missing
0.1.16 - Added new look and feel, added policy violations, added data visualization
0.1.17 - Added link to policy violation from policy name in the report
'''
import logging
import sys
import argparse
from blackduck.HubRestApi import HubInstance
from timeit import default_timer as timer
import jinja2
from datetime import datetime
import pdfkit
import requests
import os
import json
from tinydb import TinyDB, Query
from pathlib import Path
from tqdm import tqdm
import pandas as pd
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


__author__ = "Jouni Lehto"
__version__ = "0.1.17"

#Global variables
args = "" 
MAX_LIMIT=1000
# Use package-relative path for templates
templatesDir = str(Path(__file__).parent / "templates")
templateFile = "BD_Results_Distribution_by_Triage_Status_v3.html"
db = None

def get_project_group_projects(hub):
    projects = {"totalCount": 0, "items": []}
    url = f'{hub.get_urlbase()}/api/project-groups'
    headers = hub.get_headers()
    headers['Accept'] = 'application/vnd.blackducksoftware.project-detail-5+json'
    parameters={"q":f'name:{args.project_group_name}'}
    response = requests.get(url, headers=headers, params=parameters, verify = not hub.config['insecure'])
    if response.status_code == 200:
        jsondata = response.json()
        if "totalCount" in jsondata and int(jsondata["totalCount"]) > 0:
            for projectGroup in jsondata["items"]:
                get_project_groups_children_projects(hub, projectGroup, projects, headers)
    return projects

def get_project_groups_children_projects(hub, projectGroup, projects, headers):
    parameters={"limit": MAX_LIMIT}
    response = requests.get(projectGroup['_meta']['href']+"/children", headers=headers, params=parameters, verify = not hub.config['insecure'])
    if response.status_code == 200:
        childrens = response.json()
        if "totalCount" in childrens and int(childrens["totalCount"]) > MAX_LIMIT:
            downloaded = MAX_LIMIT
            while int(childrens["totalCount"]) > downloaded:
                parameters={"offset": downloaded, "limit": MAX_LIMIT}
                moreProjects = requests.get(projectGroup['_meta']['href']+"/children", headers=headers, params=parameters, verify = not hub.config['insecure'])
                childrens["items"] = childrens["items"] + moreProjects.json()["items"]
                downloaded += MAX_LIMIT
        if "totalCount" in childrens and int(childrens["totalCount"]) > 0:
            for children in childrens["items"]:
                if "isProject" in children and children["isProject"] is False:
                    get_project_groups_children_projects(hub,children, projects, headers)
                else:
                    #This phase there will always be one project, so no need for limits
                    project_response = requests.get(children['_meta']['href'], headers=headers, verify = not hub.config['insecure'])
                    if project_response.status_code == 200:
                        children_projects = project_response.json()
                        if children_projects:
                            projectList = [children_projects]
                            projects["totalCount"] = int(projects["totalCount"]) + 1
                            projects["items"] = projects["items"] + projectList
    
def get_version_snippets(hub, projectversion):
    url = f'{projectversion}/snippet-counts'
    headers = hub.get_headers()
    headers['Accept'] = 'application/vnd.blackducksoftware.internal-1+json'
    response = requests.get(url, headers=headers, verify = not hub.config['insecure'])
    jsondata = response.json()
    return jsondata

def get_project_versions(hub, project, limit=100, parameters={}):
    # paramstring = self.get_limit_paramstring(limit)
    parameters.update({'limit': limit})
    url = project['_meta']['href'] + "/versions" + hub._get_parameter_string(parameters)
    headers = hub.get_headers()
    headers['Accept'] = 'application/vnd.blackducksoftware.internal-1+json'
    response = requests.get(url, headers=headers, verify = not hub.config['insecure'])
    jsondata = response.json()
    return jsondata

def get_version_vuln_components(hub, projectversion, limit=MAX_LIMIT):
    parameters={"limit": limit}
    url = projectversion['_meta']['href'] + "/vulnerable-bom-components"
    headers = hub.get_headers()
    headers['Accept'] = 'application/vnd.blackducksoftware.bill-of-materials-6+json'
    response = requests.get(url, headers=headers, params=parameters, verify = not hub.config['insecure'])
    jsondata = response.json()
    if response.status_code == 200:
        if "totalCount" in jsondata and int(jsondata["totalCount"]) > MAX_LIMIT:
            downloaded = MAX_LIMIT
            while int(jsondata["totalCount"]) > downloaded:
                parameters={"offset": downloaded, "limit": limit}
                moreComponents = requests.get(url, headers=headers, params=parameters, verify = not hub.config['insecure'])
                if "items" in moreComponents.json():
                    jsondata["items"] = jsondata["items"] + moreComponents.json()["items"]
                downloaded += MAX_LIMIT
        return jsondata

def addFindings():
    global args, db
    hub = HubInstance(args.url, api_token=args.token, insecure=False)
    if args.project_group_name:
        projects = get_project_group_projects(hub)
    elif args.project:
        parameters={"q":"name:{}".format(args.project)}
        projects = hub.get_projects(limit=MAX_LIMIT, parameters=parameters)
    else:
        projects = hub.get_projects(limit=MAX_LIMIT)
        if "totalCount" in projects and int(projects["totalCount"]) > MAX_LIMIT:
            downloaded = MAX_LIMIT
            while int(projects["totalCount"]) > downloaded:
                parameters={"offset": downloaded}
                moreProjects = hub.get_projects(limit=MAX_LIMIT, parameters=parameters)
                projects["items"] = projects["items"] + moreProjects["items"]
                downloaded += MAX_LIMIT
    if projects and "totalCount" in projects and int(projects["totalCount"]) > 0:
        totalCounts=[]
        instanceLevelCount = {"Total": 0}
        instanceLevelCount["ProjectTotalCount"] = projects["totalCount"]
        instanceLevelCount["ProjectTotalVersionCount"] = 0
        instanceLevelCount["NEW"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["IGNORED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["DUPLICATE"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["MITIGATED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["NEEDS_REVIEW"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["PATCHED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["REMEDIATION_COMPLETE"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["REMEDIATION_REQUIRED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["NOT_AFFECTED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["AFFECTED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["UNDER_INVESTIGATION"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["NONE"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
        instanceLevelCount["SNIPPET"] = {"Total": 0, "unreviewed": 0, "reviewed": 0, "ignored": 0, "NONE": 0}
        instanceLevelCountPolicy = {}
        instanceLevelCountPolicy["UNCATEGORIZED"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
        instanceLevelCountPolicy["COMPONENT"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
        instanceLevelCountPolicy["LICENSE"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
        instanceLevelCountPolicy["OPERATIONAL"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
        instanceLevelCountPolicy["SECURITY"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
        instanceLevelCount["policyViolations"] = instanceLevelCountPolicy
        # Initialize policy details dictionary for hierarchical view
        instanceLevelCount["policyDetails"] = {}
        tqdm.write(f"Total project count: {projects['totalCount']}")
        tqdm.write("Analyzing found projects...")
        progressBar = tqdm(total=len(projects["items"]), desc="Progress", unit="project")
        for index, project in enumerate(projects["items"]):
            if index%200 == 0:
                #renew the connection after every 200 projects
                hub = HubInstance(args.url, api_token=args.token, insecure=False)
            projectLevelCount = {}
            projectId = project["_meta"]["href"].split("/")[-1]
            projectLevelCount["projectID"] = projectId
            projectLevelCount["projectName"] = project["name"]
            projectLevelCount["updatedAt"] = project["updatedAt"]
            projectLevelCount["Total"] = 0
            projectLevelCount["NEW"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["IGNORED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["DUPLICATE"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["MITIGATED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["NEEDS_REVIEW"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["PATCHED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["REMEDIATION_COMPLETE"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["REMEDIATION_REQUIRED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["NOT_AFFECTED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["AFFECTED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["UNDER_INVESTIGATION"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["NONE"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            projectLevelCount["SNIPPET"] = {"Total": 0, "unreviewed": 0, "reviewed": 0, "ignored": 0, "NONE": 0}
            projectLevelCount["isDormant"] = False
            projectLevelCountPolicy = {}
            projectLevelCountPolicy["UNCATEGORIZED"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            projectLevelCountPolicy["COMPONENT"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            projectLevelCountPolicy["LICENSE"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            projectLevelCountPolicy["OPERATIONAL"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            projectLevelCountPolicy["SECURITY"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            projectLevelCount["policyViolations"] = projectLevelCountPolicy
            # Initialize policy details dictionary for this project
            projectLevelCount["policyDetails"] = {}
            if args.cache:
                if not db.contains(Query()['projectID']==projectId):
                    getProjectMetrics(hub, project, projectLevelCount, instanceLevelCount)
                    db.insert(projectLevelCount)
                else:
                    #project data is already collected
                    projectLevelCount = db.get(Query()['projectID']==projectId)
                    if not projectLevelCount["updatedAt"] == project["updatedAt"]:
                        getProjectMetrics(hub, project, projectLevelCount, instanceLevelCount)
                        projectLevelCount["projectName"] = project["name"]
                        projectLevelCount["updatedAt"] = project["updatedAt"]
                        db.upsert(projectLevelCount)
                    else:
                        # Parse phase and distribution filters from args
                        phaseList = [p.strip().upper() for p in args.phaseCategories.split(',')] if args.phaseCategories else None
                        distributionList = [d.strip().upper() for d in args.distributionCategories.split(',')] if args.distributionCategories else None
                        
                        # Always filter cached data to match specified criteria
                        projectLevelCount = filterProjectDataByFilters(
                            projectLevelCount, 
                            versionName=args.version if args.version else None,
                            phaseCategories=phaseList,
                            distributionCategories=distributionList
                        )
                        addToTotals(projectLevelCount, instanceLevelCount)
            else:
                getProjectMetrics(hub, project, projectLevelCount, instanceLevelCount)
            totalCounts.append(projectLevelCount)
            progressBar.update()
        progressBar.close()
        instanceLevelCount["projects"] = totalCounts
        
        # Generate policyBreakdown from policyDetails for tooltip display
        instanceLevelCount["policyBreakdown"] = generatePolicyBreakdown(instanceLevelCount["policyDetails"])
        
        return instanceLevelCount
    else:
        tqdm.write("No projects found!")

def generatePolicyBreakdown(policyDetails):
    """Generate simplified policy breakdown for tooltips from full policy details"""
    policyBreakdown = {
        "COMPONENT": {},
        "LICENSE": {},
        "SECURITY": {},
        "OPERATIONAL": {},
        "UNCATEGORIZED": {}
    }
    
    for category, policies in policyDetails.items():
        if category not in policyBreakdown:
            policyBreakdown[category] = {}
        for policyName, policyData in policies.items():
            policyBreakdown[category][policyName] = policyData["totalCount"]
    
    return policyBreakdown

def filterProjectDataByFilters(projectLevelCount, versionName=None, phaseCategories=None, distributionCategories=None):
    """Filter cached project data to only include versions matching specified filters"""
    filteredProjectCount = {
        "projectID": projectLevelCount["projectID"],
        "projectName": projectLevelCount["projectName"],
        "updatedAt": projectLevelCount["updatedAt"],
        "Total": 0,
        "NEW": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "IGNORED": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "DUPLICATE": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "MITIGATED": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "NEEDS_REVIEW": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "PATCHED": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "REMEDIATION_COMPLETE": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "REMEDIATION_REQUIRED": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "NOT_AFFECTED": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "AFFECTED": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "UNDER_INVESTIGATION": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "NONE": {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0},
        "SNIPPET": {"Total": 0, "unreviewed": 0, "reviewed": 0, "ignored": 0, "NONE": 0},
        "isDormant": False,
        "policyViolations": {
            "UNCATEGORIZED": {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0},
            "COMPONENT": {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0},
            "LICENSE": {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0},
            "OPERATIONAL": {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0},
            "SECURITY": {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
        },
        "policyDetails": {},
        "projectVersionCount": 0,
        "projectVersionLevelCounts": []
    }
    
    # Filter versions by name, phase, and distribution
    if "projectVersionLevelCounts" in projectLevelCount:
        for versionData in projectLevelCount["projectVersionLevelCounts"]:
            # Check if version matches all filter criteria
            matchesVersion = versionName is None or versionData.get("versionName") == versionName
            matchesPhase = phaseCategories is None or versionData.get("phase", "").upper() in phaseCategories
            matchesDistribution = distributionCategories is None or versionData.get("distribution", "").upper() in distributionCategories
            
            # Only include version if it matches all specified filters
            if matchesVersion and matchesPhase and matchesDistribution:
                filteredProjectCount["projectVersionLevelCounts"].append(versionData)
                filteredProjectCount["projectVersionCount"] += 1
                
                # Aggregate vulnerability counts from this version
                if "vulnerableComponentCountsByRemediationStatus" in versionData:
                    vulnCounts = versionData["vulnerableComponentCountsByRemediationStatus"]
                    remediationStatuses = ["NEW", "IGNORED", "DUPLICATE", "MITIGATED", "NEEDS_REVIEW", "PATCHED", 
                                          "REMEDIATION_COMPLETE", "REMEDIATION_REQUIRED", "NOT_AFFECTED", 
                                          "AFFECTED", "UNDER_INVESTIGATION", "NONE"]
                    severities = ["MEDIUM", "HIGH", "CRITICAL", "LOW", "NONE"]
                    
                    for status in remediationStatuses:
                        if status in vulnCounts:
                            for severity in severities:
                                if severity in vulnCounts[status]:
                                    filteredProjectCount[status][severity] += vulnCounts[status][severity]
                            if "Total" in vulnCounts[status]:
                                filteredProjectCount[status]["Total"] += vulnCounts[status]["Total"]
                    
                    if "Total" in vulnCounts:
                        filteredProjectCount["Total"] += vulnCounts["Total"]
                
                # Aggregate policy violations from this version
                if "policyViolations" in versionData:
                    policyCategories = ["UNCATEGORIZED", "COMPONENT", "LICENSE", "OPERATIONAL", "SECURITY"]
                    policySeverities = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "TRIVIAL", "UNSPECIFIED"]
                    
                    for category in policyCategories:
                        if category in versionData["policyViolations"]:
                            for severity in policySeverities:
                                if severity in versionData["policyViolations"][category]:
                                    filteredProjectCount["policyViolations"][category][severity] += versionData["policyViolations"][category][severity]
                            if "Total" in versionData["policyViolations"][category]:
                                filteredProjectCount["policyViolations"][category]["Total"] += versionData["policyViolations"][category]["Total"]
                
                # Aggregate snippets from this version
                if "snippets" in versionData:
                    filteredProjectCount["SNIPPET"]["unreviewed"] += versionData["snippets"]["unreviewed"]
                    filteredProjectCount["SNIPPET"]["reviewed"] += versionData["snippets"]["reviewed"]
                    filteredProjectCount["SNIPPET"]["ignored"] += versionData["snippets"]["ignored"]
                    filteredProjectCount["SNIPPET"]["Total"] += versionData["snippets"]["Total"]
                
                # Set dormant flag
                if versionData.get("isDormant", False):
                    filteredProjectCount["isDormant"] = True
    
    # Filter policy details to only include versions matching all filter criteria
    if "policyDetails" in projectLevelCount:
        for category, policies in projectLevelCount["policyDetails"].items():
            for policyName, policyData in policies.items():
                for projectId, projectInfo in policyData["projects"].items():
                    # Filter versions within this policy using same criteria as version filtering
                    matchingVersions = [
                        v for v in projectInfo["versions"] 
                        if (versionName is None or v.get("versionName") == versionName) and
                           (phaseCategories is None or v.get("phase", "").upper() in phaseCategories) and
                           (distributionCategories is None or v.get("distribution", "").upper() in distributionCategories)
                    ]
                    if matchingVersions:
                        if category not in filteredProjectCount["policyDetails"]:
                            filteredProjectCount["policyDetails"][category] = {}
                        if policyName not in filteredProjectCount["policyDetails"][category]:
                            filteredProjectCount["policyDetails"][category][policyName] = {
                                "severity": policyData["severity"],
                                "totalCount": 0,
                                "projects": {}
                            }
                        
                        # Calculate total count for matching versions
                        versionTotalCount = sum(v["violationCount"] for v in matchingVersions)
                        filteredProjectCount["policyDetails"][category][policyName]["totalCount"] += versionTotalCount
                        
                        # Add filtered project info
                        filteredProjectCount["policyDetails"][category][policyName]["projects"][projectId] = {
                            "projectName": projectInfo["projectName"],
                            "projectID": projectId,
                            "versions": matchingVersions
                        }
    
    return filteredProjectCount


def getProjectMetrics(hub, project, projectLevelCount, instanceLevelCount):
    if args.version:
        parameters={"filter":f'{createPhaseFilterForVersions()}',"filter":f'{createDistributionFilterForVersions()}', 'q':"versionName:{}".format(args.version)}
        versions = get_project_versions(hub, project=project, limit=MAX_LIMIT, parameters=parameters)
    else:
        parameters={"filter":f'{createPhaseFilterForVersions()}',"filter":f'{createDistributionFilterForVersions()}'}
        versions = get_project_versions(hub, project=project, limit=MAX_LIMIT, parameters=parameters)
    if versions and "totalCount" in versions and int(versions["totalCount"]) > 0:
        instanceLevelCount["ProjectTotalVersionCount"] = instanceLevelCount["ProjectTotalVersionCount"] + int(versions["totalCount"])
        projectLevelCount["projectVersionCount"] = versions["totalCount"]
        projectVersionsCounts = []
        for version in versions["items"]:
            versionLevelCounts = {}
            projectVersionId = version["_meta"]["href"].split("/")[-1]
            versionLevelCounts["versionID"] = projectVersionId
            versionLevelCounts["versionName"] = version["versionName"] if "versionName" in version else "-"
            versionLevelCounts["lastScanDate"] = getDate(version, "lastScanDate")
            versionLevelCounts["isDormant"] = False
            if args.sinceDays and args.sinceDays > 0:
                if "lastScanDate" in version:
                    versionLevelCounts["isDormant"] = isDormant(version["lastScanDate"])
                    if projectLevelCount["isDormant"] is False:
                        #Set isDormant to project level only if not set True yet
                        projectLevelCount["isDormant"] = versionLevelCounts["isDormant"]
                else:
                    versionLevelCounts["isDormant"] = True
                    if projectLevelCount["isDormant"] is False:
                        #Set isDormant to project level only if not set True yet
                        projectLevelCount["isDormant"] = versionLevelCounts["isDormant"]
            versionLevelCounts["phase"] = version["phase"] if "phase" in version else "-"
            versionLevelCounts["distribution"] = version["distribution"] if "distribution" in version else "-"
            #Check if project version has snippets scan present
            snippetCounts = get_version_snippets(hub, version["_meta"]["href"])
            if "snippetScanPresent" in snippetCounts and snippetCounts["snippetScanPresent"]:
                projectVersionSnippetCounts = {"unreviewed": snippetCounts["unreviewedCount"], 
                                            "reviewed": snippetCounts["reviewedCount"],
                                            "ignored": snippetCounts["ignoredCount"],
                                            "Total": snippetCounts["totalCount"]}
                versionLevelCounts["snippets"] = projectVersionSnippetCounts
                #Project level snippet count
                projectLevelCount["SNIPPET"]["unreviewed"] = projectLevelCount["SNIPPET"]["unreviewed"] + snippetCounts["unreviewedCount"]
                projectLevelCount["SNIPPET"]["reviewed"] = projectLevelCount["SNIPPET"]["reviewed"] + snippetCounts["reviewedCount"]
                projectLevelCount["SNIPPET"]["ignored"] = projectLevelCount["SNIPPET"]["ignored"] + snippetCounts["ignoredCount"]
                projectLevelCount["SNIPPET"]["Total"] = projectLevelCount["SNIPPET"]["Total"] + snippetCounts["totalCount"]
                #Instance level snippet count
                instanceLevelCount["SNIPPET"]["unreviewed"] = instanceLevelCount["SNIPPET"]["unreviewed"] + snippetCounts["unreviewedCount"]
                instanceLevelCount["SNIPPET"]["reviewed"] = instanceLevelCount["SNIPPET"]["reviewed"] + snippetCounts["reviewedCount"]
                instanceLevelCount["SNIPPET"]["ignored"] = instanceLevelCount["SNIPPET"]["ignored"] + snippetCounts["ignoredCount"]
                instanceLevelCount["SNIPPET"]["Total"] = instanceLevelCount["SNIPPET"]["Total"] + snippetCounts["totalCount"]
            else:
                projectVersionSnippetCounts = {"unreviewed": 0, 
                                            "reviewed": 0,
                                            "ignored": 0,
                                            "Total": 0}
                versionLevelCounts["snippets"] = projectVersionSnippetCounts
            # Get project policy violations
            projectPolicyViolations = getPolicyViolations(hub=hub, projectversion=version)
            versionLevelCountPolicy = {}
            versionLevelCountPolicy["UNCATEGORIZED"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            versionLevelCountPolicy["COMPONENT"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            versionLevelCountPolicy["LICENSE"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            versionLevelCountPolicy["OPERATIONAL"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            versionLevelCountPolicy["SECURITY"] = {"Total": 0, "BLOCKER": 0, "CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "TRIVIAL": 0, "UNSPECIFIED": 0}
            for policyViolation in projectPolicyViolations.get("items", []):
                category = policyViolation.get("category", "UNCATEGORIZED")
                severity = policyViolation.get("severity", "UNSPECIFIED")
                count = policyViolation.get("bomViolationCount", 0)
                policyName = policyViolation.get("name", "Unnamed Policy")
                
                # By category and by severity on instance level
                byCategory = instanceLevelCount["policyViolations"][category]
                byCategory[severity] = byCategory[severity] + count
                byCategory["Total"] = byCategory["Total"] + count
                # By category and by severity on project level
                byCategory = projectLevelCount["policyViolations"][category]
                byCategory[severity] = byCategory[severity] + count
                byCategory["Total"] = byCategory["Total"] + count
                # By category and by severity on project version level
                byCategory = versionLevelCountPolicy[category]
                byCategory[severity] = byCategory[severity] + count
                byCategory["Total"] = byCategory["Total"] + count
                
                # Build hierarchical policy details structure at instance level: Category -> Policy Name -> Projects -> Versions
                if category not in instanceLevelCount["policyDetails"]:
                    instanceLevelCount["policyDetails"][category] = {}
                if policyName not in instanceLevelCount["policyDetails"][category]:
                    instanceLevelCount["policyDetails"][category][policyName] = {
                        "severity": severity,
                        "totalCount": 0,
                        "projects": {}
                    }
                instanceLevelCount["policyDetails"][category][policyName]["totalCount"] += count
                
                # Add project to this policy's violations
                projectId = projectLevelCount["projectID"]
                if projectId not in instanceLevelCount["policyDetails"][category][policyName]["projects"]:
                    instanceLevelCount["policyDetails"][category][policyName]["projects"][projectId] = {
                        "projectName": projectLevelCount["projectName"],
                        "projectID": projectId,
                        "versions": []
                    }
                
                # Add version details to instance level
                instanceLevelCount["policyDetails"][category][policyName]["projects"][projectId]["versions"].append({
                    "versionName": version["versionName"],
                    "versionID": version["_meta"]["href"].split("/")[-1],
                    "phase": version.get("phase", "UNKNOWN"),
                    "distribution": version.get("distribution", "UNKNOWN"),
                    "lastScanDate": getDate(version, "settingUpdatedAt"),
                    "isDormant": versionLevelCounts["isDormant"],
                    "violationCount": count,
                    "severity": severity
                })
                
                # Build hierarchical policy details structure at project level for caching
                if category not in projectLevelCount["policyDetails"]:
                    projectLevelCount["policyDetails"][category] = {}
                if policyName not in projectLevelCount["policyDetails"][category]:
                    projectLevelCount["policyDetails"][category][policyName] = {
                        "severity": severity,
                        "totalCount": 0,
                        "projects": {}
                    }
                projectLevelCount["policyDetails"][category][policyName]["totalCount"] += count
                
                # Add this project to project level policy details
                if projectId not in projectLevelCount["policyDetails"][category][policyName]["projects"]:
                    projectLevelCount["policyDetails"][category][policyName]["projects"][projectId] = {
                        "projectName": projectLevelCount["projectName"],
                        "projectID": projectId,
                        "versions": []
                    }
                
                # Add version details to project level
                projectLevelCount["policyDetails"][category][policyName]["projects"][projectId]["versions"].append({
                    "versionName": version["versionName"],
                    "versionID": version["_meta"]["href"].split("/")[-1],
                    "phase": version.get("phase", "UNKNOWN"),
                    "distribution": version.get("distribution", "UNKNOWN"),
                    "lastScanDate": getDate(version, "settingUpdatedAt"),
                    "isDormant": versionLevelCounts["isDormant"],
                    "violationCount": count,
                    "severity": severity
                })
            versionLevelCounts["policyViolations"] = versionLevelCountPolicy
            vulnerableComponents = get_version_vuln_components(hub=hub, projectversion=version)
            vulnerableComponentCountsByRemediationStatus = {"Total": 0}
            vulnerableComponentCountsByRemediationStatus["NEW"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["IGNORED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["DUPLICATE"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["MITIGATED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["NEEDS_REVIEW"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["PATCHED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["REMEDIATION_COMPLETE"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["REMEDIATION_REQUIRED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["NOT_AFFECTED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["AFFECTED"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["UNDER_INVESTIGATION"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            vulnerableComponentCountsByRemediationStatus["NONE"] = {"Total": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "LOW": 0, "NONE": 0}
            if vulnerableComponents and "totalCount" in vulnerableComponents and int(vulnerableComponents["totalCount"]) > 0:
                for vulnerableComponent in vulnerableComponents["items"]:
                    if "vulnerabilityWithRemediation" in vulnerableComponent:
                        if not "remediationStatus" in vulnerableComponent["vulnerabilityWithRemediation"]:
                            vulnerableComponent["vulnerabilityWithRemediation"]["remediationStatus"] = "NONE"
                        if not "severity" in vulnerableComponent["vulnerabilityWithRemediation"]:
                            vulnerableComponent["vulnerabilityWithRemediation"]["severity"] = "NONE"
                        # By remediation status and by severity on project version level
                        byRemediationStatus = vulnerableComponentCountsByRemediationStatus[vulnerableComponent["vulnerabilityWithRemediation"]["remediationStatus"]]
                        byRemediationStatus["Total"] = byRemediationStatus["Total"] + 1
                        byRemediationStatus[vulnerableComponent["vulnerabilityWithRemediation"]["severity"]] = byRemediationStatus[vulnerableComponent["vulnerabilityWithRemediation"]["severity"]] + 1
                        vulnerableComponentCountsByRemediationStatus["Total"] = vulnerableComponentCountsByRemediationStatus["Total"] + 1
                        # By remediation status and by severity on project level
                        byRemediationStatus = projectLevelCount[vulnerableComponent["vulnerabilityWithRemediation"]["remediationStatus"]]
                        byRemediationStatus["Total"] = byRemediationStatus["Total"] + 1
                        byRemediationStatus[vulnerableComponent["vulnerabilityWithRemediation"]["severity"]] = byRemediationStatus[vulnerableComponent["vulnerabilityWithRemediation"]["severity"]] + 1
                        projectLevelCount["Total"] = projectLevelCount["Total"] + 1
                        # By remediation status and by severity on Black Duck instance level
                        byRemediationStatus = instanceLevelCount[vulnerableComponent["vulnerabilityWithRemediation"]["remediationStatus"]]
                        byRemediationStatus["Total"] = byRemediationStatus["Total"] + 1
                        byRemediationStatus[vulnerableComponent["vulnerabilityWithRemediation"]["severity"]] = byRemediationStatus[vulnerableComponent["vulnerabilityWithRemediation"]["severity"]] + 1
                        instanceLevelCount["Total"] = instanceLevelCount["Total"] + 1
            else:
                if logging.getLogger().isEnabledFor(logging.DEBUG):
                    tqdm.write(f"Project {project['name']} version {version['versionName']} didn't have any vulnerable components.")
            versionLevelCounts["vulnerableComponentCountsByRemediationStatus"] = vulnerableComponentCountsByRemediationStatus
            projectVersionsCounts.append(versionLevelCounts)
        projectLevelCount["projectVersionLevelCounts"] = projectVersionsCounts

def getPolicyViolations(hub, projectversion):
    url = projectversion['_meta']['href'] + "/policy-rules"
    headers = hub.get_headers()
    headers['Accept'] = 'application/vnd.blackducksoftware.bill-of-materials-7+json'
    response = requests.get(url, headers=headers, verify = not hub.config['insecure'])
    jsondata = response.json()
    return jsondata

def isDormant(scanninDate):
    if scanninDate:
        findingDatetime = datetime.strptime(scanninDate, "%Y-%m-%dT%H:%M:%S.%fZ")
        comparedatetime = findingDatetime
        return True if (datetime.now()-comparedatetime).days > args.sinceDays else False
    else:
        return False
    
def getDate(source, whichDate):
    datetime_to_modify = None
    if whichDate in source and source[whichDate]:
       datetime_to_modify = datetime.strptime(source[whichDate], "%Y-%m-%dT%H:%M:%S.%fZ")
    if datetime_to_modify:
        return datetime.strftime(datetime_to_modify, "%B %d, %Y")
    return "-"

def addToTotals(projectCount, instanceLevelCount):
    remediationstatuses = ["NEW","IGNORED","DUPLICATE","MITIGATED","NEEDS_REVIEW","PATCHED","REMEDIATION_COMPLETE","REMEDIATION_REQUIRED", "NOT_AFFECTED", "AFFECTED", "UNDER_INVESTIGATION", "NONE"]
    severities = ["MEDIUM","HIGH","CRITICAL","LOW", "NONE", "Total"]
    policySeverities = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "TRIVIAL", "UNSPECIFIED", "Total"]
    policyCategories = ["UNCATEGORIZED", "COMPONENT", "LICENSE", "OPERATIONAL", "SECURITY"]
    
    for remediation in remediationstatuses:
        for severity in severities:
            if remediation in projectCount and severity in projectCount[remediation]:
                instanceLevelCount[remediation][severity] = instanceLevelCount[remediation][severity] + projectCount[remediation][severity]
    instanceLevelCount["Total"] = instanceLevelCount["Total"] + projectCount["Total"]
    if "projectVersionCount" in projectCount:
        instanceLevelCount["ProjectTotalVersionCount"] = instanceLevelCount["ProjectTotalVersionCount"] + projectCount["projectVersionCount"]
    instanceLevelCount["SNIPPET"]["unreviewed"] = instanceLevelCount["SNIPPET"]["unreviewed"] + projectCount["SNIPPET"]["unreviewed"]
    instanceLevelCount["SNIPPET"]["reviewed"] = instanceLevelCount["SNIPPET"]["reviewed"] + projectCount["SNIPPET"]["reviewed"]
    instanceLevelCount["SNIPPET"]["ignored"] = instanceLevelCount["SNIPPET"]["ignored"] + projectCount["SNIPPET"]["ignored"]
    instanceLevelCount["SNIPPET"]["Total"] = instanceLevelCount["SNIPPET"]["Total"] + projectCount["SNIPPET"]["Total"]
    
    # Aggregate policy violations from cached project data
    if "policyViolations" in projectCount:
        for category in policyCategories:
            if category in projectCount["policyViolations"]:
                for severity in policySeverities:
                    if severity in projectCount["policyViolations"][category]:
                        instanceLevelCount["policyViolations"][category][severity] += projectCount["policyViolations"][category][severity]
    
    # Aggregate policy details from cached project data
    if "policyDetails" in projectCount:
        for category, policies in projectCount["policyDetails"].items():
            if category not in instanceLevelCount["policyDetails"]:
                instanceLevelCount["policyDetails"][category] = {}
            for policyName, policyData in policies.items():
                if policyName not in instanceLevelCount["policyDetails"][category]:
                    instanceLevelCount["policyDetails"][category][policyName] = {
                        "severity": policyData["severity"],
                        "totalCount": 0,
                        "projects": {}
                    }
                instanceLevelCount["policyDetails"][category][policyName]["totalCount"] += policyData["totalCount"]
                # Merge project data
                for projectId, projectInfo in policyData["projects"].items():
                    if projectId not in instanceLevelCount["policyDetails"][category][policyName]["projects"]:
                        instanceLevelCount["policyDetails"][category][policyName]["projects"][projectId] = projectInfo
                    else:
                        # Append versions if project already exists
                        instanceLevelCount["policyDetails"][category][policyName]["projects"][projectId]["versions"].extend(projectInfo["versions"])


def createPhaseFilterForVersions():
    phaseCategories = args.phaseCategories.split(',')
    phaseCategoryOptions = ""
    for phaseCategory in phaseCategories:
        phaseCategoryOptions += f'phase:{phaseCategory.strip().upper()},'
    return phaseCategoryOptions[:-1]

def createDistributionFilterForVersions():
    distributionCategories = args.distributionCategories.split(',')
    distributionCategoryOptions = ""
    for distributionCategory in distributionCategories:
        distributionCategoryOptions += f'distribution:{distributionCategory.strip().upper()},'
    return distributionCategoryOptions[:-1]

def generate_pdf_with_playwright(html_file_path, output_path):
    """Generate PDF using Playwright from HTML file for proper chart rendering"""
    try:
        with sync_playwright() as p:
            # Launch browser with optimized settings
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            context = browser.new_context()
            page = context.new_page()
            
            # Set shorter timeout
            page.set_default_timeout(15000)  # 15 seconds
            
            # Load HTML file with 'load' event instead of 'networkidle' for faster loading
            page.goto(f'file:///{html_file_path.replace(chr(92), "/")}', wait_until='load', timeout=15000)
            
            # Wait for Chart.js to be loaded and charts to render (reduced wait time)
            page.wait_for_function("typeof Chart !== 'undefined'", timeout=5000)
            
            # Wait for canvas elements (charts) with shorter timeout
            try:
                page.wait_for_selector('canvas', timeout=2000)
                # Give charts minimal time to render
                page.wait_for_timeout(500)
            except:
                # If no charts, just wait a bit
                page.wait_for_timeout(1000)
            
            # Generate PDF with compression
            page.pdf(
                path=output_path, 
                format='A4', 
                print_background=True,
                prefer_css_page_size=False,
                margin={'top': '0.5cm', 'bottom': '0.5cm', 'left': '0.5cm', 'right': '0.5cm'}
            )
            
            browser.close()
            return True
    except Exception as e:
        tqdm.write(f"Playwright error: {str(e)}")
        return False

def main():
    """Main entry point for the Black Duck Remediation Metrics tool."""
    global args, db
    try:
        start = timer()
        #Initialize the parser
        parser = argparse.ArgumentParser(
            description="Black Duck Metrics by Remediation Status."
        )
        #Parse commandline arguments
        parser.add_argument('--url', default=os.environ.get('BD_URL'), help="Baseurl for Black Duck Hub", required=False)
        parser.add_argument('--token', default=os.environ.get('BD_TOKEN'), help="BD Access token", required=False)
        parser.add_argument('--project', help="BD project name", required=False)
        parser.add_argument('--project_group_name', help="BD project group name", required=False)
        parser.add_argument('--version', help="BD project version name", required=False)
        parser.add_argument('--phaseCategories', help="Comma separated list of version phases, which will be selected. \
            Options are [PLANNING,DEVELOPMENT,RELEASED,DEPRECATED,ARCHIVED,PRERELEASE], default=\"PLANNING,DEVELOPMENT,RELEASED,DEPRECATED,ARCHIVED,PRERELEASE\"", default="PLANNING,DEVELOPMENT,RELEASED,DEPRECATED,ARCHIVED,PRERELEASE")
        parser.add_argument('--distributionCategories', help="Comma separated list of version distributions, which will be selected. \
            Options are [EXTERNAL,SAAS,INTERNAL,OPENSOURCE], default=\"EXTERNAL,SAAS,INTERNAL,OPENSOURCE\"", default="EXTERNAL,SAAS,INTERNAL,OPENSOURCE")
        parser.add_argument('--log_level', help="Will print more info... default=INFO", default="INFO")
        parser.add_argument('--html', action='store_true', help='generate HTML report')
        parser.add_argument('--pdf', action='store_true', help='generate PDF report')
        parser.add_argument('--json', action='store_true', help='generate json report')
        parser.add_argument('--csv', action='store_true', help='generate csv report')
        parser.add_argument('--dashboard', action='store_true', help='generate interactive dashboard HTML report with charts')
        parser.add_argument('--dir', default='.', help='output directory (default: current directory)')
        parser.add_argument('--db_file', default='bd_remediation_db.json', help='TinyDB database file.')
        parser.add_argument('--cache', action='store_true', help='use tinyDB as a cache')
        parser.add_argument('--cache_truncate', action='store_true', help='will clean the given cache file')
        parser.add_argument('--sinceDays', type=int, default=30, help="The number of days before which to find project version dormant. (Default 30 days)", required=False)
        args = parser.parse_args()
        #Initializing the logger
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("blackduck.HubRestApi").setLevel(logging.WARNING)
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s: %(message)s', stream=sys.stderr, level=args.log_level)
        #Printing out the version number
        tqdm.write("Black Duck Triage Extractor version: " + __version__)
        if not args.url:
            tqdm.write("Black Duck URL is not given. You need to give it with --url or as an BD_URL environment variable!")
            exit()
        if not args.token:
            tqdm.write("Black Duck Access Token is not given. You need to give it with --token or as an BD_TOKEN environment variable!")
            exit()
        #Removing / -mark from end of url, if it exists
        args.url = f'{args.url if not args.url.endswith("/") else args.url[:-1]}'
        #DB Initialization
        db_file = args.dir + '/' + args.db_file
        path = Path(db_file)
        db = TinyDB(path, access_mode="r+", sort_keys=True, indent=3, separators=(',', ': '))
        db.default_table_name = "projects"
        if args.cache_truncate:
            db.truncate()
        totals = addFindings()
        db.close()
        if totals:
            if int(totals['Total']) > 0:
                timeFilenameFormat = '%Y%m%d%H%M%S'
                timeFormat = '%Y-%m-%d %H:%M:%S'
                polarisTimeFormat = '%Y-%m-%dT%H:%M:%S.%fZ'
                timestamp = datetime.today().strftime(timeFilenameFormat)
                outputPrefix = 'triageReport_bd_' + timestamp
                if (args.dashboard):
                    # Generate interactive dashboard with Chart.js
                    tqdm.write("Creating interactive dashboard...")
                    templateLoader = jinja2.FileSystemLoader(searchpath=templatesDir)
                    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
                    dashboardTemplate = templateEnv.get_template('BD_Results_Triage_Dashboard.html')
                    
                    dashboardHtml = dashboardTemplate.render(
                        bdURL = args.url,
                        reportTime = datetime.today().strftime(timeFormat),
                        data = totals,
                        dataJson = json.dumps(totals),
                        phases = args.phaseCategories,
                        distibutions = args.distributionCategories,
                        projectGroup = args.project_group_name,
                        project = args.project,
                        version = args.version,
                        sinceDays = args.sinceDays
                    )
                    
                    dashboardFile = args.dir + '/dashboard_bd_' + timestamp + '.html'
                    with open(dashboardFile, "w", encoding='utf-8') as fh:
                        fh.write(dashboardHtml)
                    tqdm.write(f"Dashboard created: {dashboardFile}")
                if (args.html or args.pdf):
                    # Setup template stuff
                    tqdm.write("Creating template for HTML and PDF reports....")
                    templateLoader = jinja2.FileSystemLoader(searchpath=templatesDir)
                    templateEnv = jinja2.Environment(loader=templateLoader, autoescape=True)
                    template = templateEnv.get_template(templateFile)
                    tqdm.write("Done")

                    tqdm.write("Rendering the template for HTML and PDF reports....")
                    htmlText = template.render(bdURL = args.url,
                                            reportTime = datetime.today().strftime(timeFormat),
                                            phases = args.phaseCategories,
                                            distibutions = args.distributionCategories,
                                            projectGroup = args.project_group_name,
                                            project = args.project,
                                            version = args.version,
                                            sinceDays = args.sinceDays,
                                            totals = totals)
                    tqdm.write("Done")

                    if (args.html):
                        tqdm.write("Creating HTML report...")
                        file = args.dir + '/' + outputPrefix + '.html'
                        with open(file, "w", encoding='utf-8') as fh:
                            fh.write(htmlText)
                        tqdm.write("Done")
                    
                    if (args.pdf):
                        tqdm.write("Creating PDF report...")
                        pdf_path = args.dir + '/' + outputPrefix + '.pdf'
                        
                        # Always create HTML file first for PDF generation
                        html_path = args.dir + '/' + outputPrefix + '_temp.html'
                        if args.html:
                            # Use the already created HTML file
                            html_path = args.dir + '/' + outputPrefix + '.html'
                        else:
                            # Create temporary HTML file
                            with open(html_path, "w", encoding='utf-8') as fh:
                                fh.write(htmlText)
                        
                        if PLAYWRIGHT_AVAILABLE:
                            tqdm.write("Generating PDF with Playwright...")
                            success = generate_pdf_with_playwright(html_path, pdf_path)
                            if success:
                                tqdm.write("Done (using Playwright for chart rendering)")
                            else:
                                tqdm.write("Playwright PDF generation failed. Falling back to pdfkit...")
                                options = {'enable-local-file-access': None}
                                pdfkit.from_string(htmlText, pdf_path, options=options)
                                tqdm.write("Done (using pdfkit - charts may not render)")
                        else:
                            tqdm.write("Warning: Playwright not installed. Charts will not render in PDF.")
                            tqdm.write("Install with: pip install playwright && playwright install chromium")
                            options = {'enable-local-file-access': None}
                            pdfkit.from_string(htmlText, pdf_path, options=options)
                            tqdm.write("Done (using pdfkit - charts not rendered)")
                        
                        # Clean up temp HTML file if it was created
                        if not args.html and os.path.exists(html_path):
                            try:
                                os.remove(html_path)
                            except:
                                pass
                if (args.json):
                    tqdm.write("Creating JSON report...")
                    file = args.dir + '/' + outputPrefix + '.json'
                    f = open(file, "w", encoding="utf8")
                    f.write(json.dumps(totals, indent=3))
                    f.close()
                    tqdm.write("Done")
                if args.csv:
                    tqdm.write("Creating CVS report...")
                    df = pd.json_normalize(totals)
                    df.to_csv(args.dir + '/' + outputPrefix + '.csv', index=False, encoding='utf-8')
            else:
                tqdm.write("No vulnerable components found!")
        end = timer()
        usedTime = end - start
        tqdm.write(f"Took: {usedTime} seconds.")
        if totals and totals['ProjectTotalCount'] > 0:
            tqdm.write(f'average time per project: {usedTime/totals["ProjectTotalCount"]} seconds.')
        tqdm.write("Done")
    except Exception as e:
        if db:
            db.close()
        tqdm.write(f"Exception occurred: {e}")
        raise SystemError(e)

if __name__ == '__main__':
    main()
