# UCLouvain-Course-Scraper

Scraper for UCLouvain courses.

## Description

This repo provides a Python script to scrape course information from the UCLouvain (Université catholique de Louvain) course catalog. It allows you to retrieve detailed information about courses, filter them based on various criteria, and save the data into JSON files for further analysis.

## Features

- **Scrape course information** from UCLouvain's online course catalog.
- **Retrieve detailed course data** such as title, credits, quadrimester, teachers, and more.
- **Filter courses** based on credits, quadrimester, included keywords, and excluded keywords.
- **Save scraped data** into JSON files to avoid redundant scraping.
- **Output filtered courses** to the console and save them into a separate JSON file.

## Example

Suppose you are interested in scraping all courses in quadrimester 1 (`Q1`) that have between 2 and 6 credits.

### Set the `filter_params` as follows:

```python
filter_params = {
    'min_credits': 2,
    'max_credits': 6,
    'quadrimester': ['Q1'],
    'include_keywords': None,
    'exclude_keywords': None
}
```

### Run the script
```bash
python scraper.py
```

### Sample Output

```vbnet
Scraping UCLouvain course information...
Data folder 'master_courses_24_25' exists. Loading data from JSON files...
10222 courses loaded.
Title: Cloud Computing
Credits: 5.00
Quadrimester: Q1
URL: https://uclouvain.be/cours-2024-linfo2145
Teachers: *
Responsible Entity: INFO
================================================================================
Title: Software engineering project
Credits: 6.00
Quadrimester: Q1
URL: https://uclouvain.be/cours-2024-linfo2255
Teachers: *
Responsible Entity: INFO
================================================================================
...
```

## Custom Filtering

You can customize the filters to include or exclude courses based on specific keywords in different sections.

### Include Keywords Example
To include only courses that mention **"machine learning"** in any section:

```python
filter_params = {
    'min_credits': None,
    'max_credits': None,
    'quadrimester': None,
    'include_keywords': {'global': ['machine learning']},
    'exclude_keywords': None
}
```

### Exclude Keywords Example
To exclude courses that mention "statistics" in the content section:

```python
filter_params = {
    'min_credits': None,
    'max_credits': None,
    'quadrimester': None,
    'include_keywords': None,
    'exclude_keywords': {'content': ['statistics']}
}
```

## Data Folder
- The script saves all scraped data into a folder (`master_courses_24_25` by default).
- If the data folder exists, the script will **load data from the JSON files** instead of scraping again.
- To **force re-scraping**, delete the data folder or change the name.
- The filtered courses are saved in `filtered_courses.json` by default.

