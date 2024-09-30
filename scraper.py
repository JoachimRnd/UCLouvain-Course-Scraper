"""
UCLouvainCourseScraper: Scraper for UCLouvain courses.

Author: Joachim Renard
Date: 2024-09-30
License: MIT
"""

import requests
from bs4 import BeautifulSoup
import json
import os

class UCLouvainCourseScraper:
    SECTION_MAPPING = {
        'Enseignants': 'teachers',
        "Langue d'enseignement": 'teaching_language',
        'Préalables': 'prerequisites',
        'Thèmes abordés': 'topics_covered',
        "Acquis d'apprentissage": 'learning_outcomes',
        'Contenu': 'content',
        "Méthodes d'enseignement": 'teaching_methods',
        "Modes d'évaluation des acquis des étudiants": 'assessment_methods',
        'Autres infos': 'other_info',
        'Ressources en ligne': 'online_resources',
        'Bibliographie': 'bibliography',
        'Support de cours': 'course_materials',
        'Faculté ou entité en charge': 'responsible_entity',
    }
    

    def __init__(self, base_url, data_folder='master_courses_24_25', output_filtered_filename='filtered_courses.json'):
        self.base_url = base_url
        self.data_folder = data_folder
        self.filtered_courses = []
        self.filtered_course_urls = set()
        self.output_filtered_filename = output_filtered_filename

    def get_programs(self):
        """Retrieves all program links from the given URL.

        Returns:
            list: A list of unique URLs (str) for each program found on the page.
        """
        response = requests.get(self.base_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        links = []

        # Find all links to a programs (e.g. Bachelor or Master)
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/prog-2024-' in href:
                url = href if href.startswith('http') else 'https://uclouvain.be' + href
                links.append(url)
        
        return list(set(links))

    def get_course_links(self, url):
        """Retrieves all course links for a given program.

        Args:
            url (str): The URL of the program's page.

        Returns:
            list: A list of unique URLs (str) for each course found in a program.
        """
        programme_url = f"{url}-programme"
        response = requests.get(programme_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        course_links = []

        # Find all links to courses
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if 'cours-2024-' in href:
                course_url = href if href.startswith('http') else 'https://uclouvain.be/' + href
                course_links.append(course_url)
        
        return list(set(course_links))

    def get_course_info(self, course_url):
        """Scrapes course information from a given course URL.

        Args:
            course_url (str): The URL of the course page to scrape.

        Returns:
            dict or None: A dictionary containing the course information if successful; otherwise, None.
        """
        course_info = {}
        try:
            response = requests.get(course_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {course_url}: {e}")
            return None

        course_info['url'] = course_url

        # Extract title
        title_tag = soup.find('h1')
        course_info['title'] = title_tag.get_text(strip=True) if title_tag else None

        # Extract credits, hours, quadrimester
        fa_row_1 = soup.find('div', class_='row fa_row_1')
        if fa_row_1:
            fa_cells = fa_row_1.find_all('div', class_='fa_cell_0')
            credits_text = fa_cells[0].get_text(strip=True) if len(fa_cells) > 0 else None
            if credits_text and 'crédit' in credits_text:
                course_info['credits'] = credits_text.split(' ')[0]
            else:
                course_info['credits'] = None

            course_info['hours'] = fa_cells[1].get_text(strip=True) if len(fa_cells) > 1 else None
            course_info['quadrimester'] = fa_cells[2].get_text(strip=True) if len(fa_cells) > 2 else None
        else:
            course_info['credits'] = None
            course_info['hours'] = None
            course_info['quadrimester'] = None

        # Extract other sections
        fa_main_body = soup.find('div', class_='fa_main_body')
        if fa_main_body:
            # Find all rows
            fa_rows = fa_main_body.find_all('div', class_='row fa_row')
            for fa_row in fa_rows:
                title_div = fa_row.find('div', class_='col-sm-2 fa_cell_1')
                content_div = fa_row.find('div', class_='col-sm-10 fa_cell_2')
                if title_div and content_div:
                    section_title = title_div.get_text(separator=' ', strip=True)
                    # Standardization
                    section_title_clean = ' '.join(section_title.split()).lower()
                    # Find the corresponding key
                    key = None
                    for fr_title, en_key in self.SECTION_MAPPING.items():
                        if fr_title.lower() == section_title_clean:
                            key = en_key
                            break
                    # Extract content
                    if key:
                        if key == 'teachers':
                            teachers = [a.get_text(strip=True) for a in content_div.find_all('a')]
                            course_info[key] = teachers
                        elif key == 'teaching_language':
                            lang_text = content_div.get_text(separator=' ', strip=True)
                            # Remove the "Facilités pour suivre le cours en français"
                            lang_text = lang_text.split('> Facilités')[0].strip()
                            course_info[key] = lang_text
                        else:
                            content_text = content_div.get_text(separator=' ', strip=True)
                            if key == 'responsible_entity':
                                content_text = content_text.replace('> ', '')
                            course_info[key] = content_text
                    else:
                        # Store unrecognized sections as is
                        content_text = content_div.get_text(separator=' ', strip=True)
                        course_info[section_title_clean] = content_text

        return course_info

    def filter_course(
        self,
        course,
        min_credits=None,
        max_credits=None,
        quadrimester=None,
        include_keywords=None,
        exclude_keywords=None
    ):
        """Filters a course dictionary based on specified criteria.

        This function applies multiple filtering criteria to a course dictionary,
        such as credit range, quadrimester, included keywords, and excluded keywords.
        It supports both global and section-specific keyword searches.
        If the course matches all the criteria, it's returned; otherwise, None is returned.

        Args:
            course (dict): The course information dictionary to be filtered.
            min_credits (float, optional): Minimum number of credits required.
            max_credits (float, optional): Maximum number of credits allowed.
            quadrimester (list of str, optional): List of quadrimesters to match.
                Example: ['Q1'], ['Q1,'Q2'], ['Q1Q2']
            include_keywords (dict, optional): Keywords that must be included.
                Format: {'section_name': ['keyword1', 'keyword2'], 'global': ['keyword3']}
            exclude_keywords (dict, optional): Keywords that must not be present.
                Format: {'section_name': ['keyword1', 'keyword2'], 'global': ['keyword3']}

        Returns:
            dict or None: The original course dictionary if it matches all criteria; otherwise, None.
        """
        match = True

        # Filter by credits
        if min_credits or max_credits:
            try:
                credits = float(course['credits'])
                if min_credits and credits < min_credits:
                    match = False
                if max_credits and credits > max_credits:
                    match = False
            except (TypeError, ValueError):
                match = False

        # Filter by quadrimester
        if quadrimester and course.get('quadrimester'):
            course_quadrimester = course['quadrimester'].lower().replace('et', '').replace(' ', '').upper()
            if course_quadrimester not in quadrimester:
                match = False

        # Prepare the course text for global keyword search
        all_text = ' '.join(
            ' '.join(value) if isinstance(value, list) else value
            for value in course.values() if isinstance(value, (list, str))
        )

        # Initialize include_match and exclude_match
        include_match = True
        exclude_match = False

        # Filter by included keywords
        if include_keywords:
            # Global keywords
            global_includes = include_keywords.get('global', [])
            if global_includes:
                if not any(keyword.lower() in all_text.lower() for keyword in global_includes):
                    include_match = False

            # Section-specific keywords
            for section, keywords in include_keywords.items():
                if section == 'global':
                    continue
                section_content = course.get(section, '')
                if isinstance(section_content, list):
                    section_content = ' '.join(section_content)
                if not any(keyword.lower() in section_content.lower() for keyword in keywords):
                    include_match = False
                    break

        # Filter by excluded keywords
        if exclude_keywords:
            # Global keywords
            global_excludes = exclude_keywords.get('global', [])
            if global_excludes:
                if any(keyword.lower() in all_text.lower() for keyword in global_excludes):
                    exclude_match = True

            # Section-specific keywords
            for section, keywords in exclude_keywords.items():
                if section == 'global':
                    continue
                section_content = course.get(section, '')
                if isinstance(section_content, list):
                    section_content = ' '.join(section_content)
                if any(keyword.lower() in section_content.lower() for keyword in keywords):
                    exclude_match = True
                    break

        # Decide if the course matches
        if include_keywords and not include_match:
            print("include_keywords", course['title'])
            match = False
        if exclude_keywords and exclude_match:
            print("exclude_keywords", course['title'])
            match = False

        return course if match else None

    def scrape(self, filter_params):
        """
        Main method to scrape UCLouvain course information.

        This method runs the entire scraping process:
        - Checks if the data folder exists.
            - If it exists, loads data from JSON files and applies filters.
            - If it does not exist, performs scraping, saves data, and applies filters.
        - Saves filtered courses into a separate JSON file.
        - Prints progress and filtered course information.

        Args:
            filter_params (dict): Parameters to filter courses, which may include:
                - min_credits (float, optional): Minimum number of credits required.
                - max_credits (float, optional): Maximum number of credits allowed.
                - quadrimester (list of str, optional): List of quadrimesters to match.
                    Example: ['Q1'], ['Q2'], ['Q1Q2']
                - include_keywords (dict, optional): Keywords that must be included.
                    Format: {'section_name': ['keyword1', 'keyword2'], 'global': ['keyword3']}
                - exclude_keywords (dict, optional): Keywords that must not be present.
                    Format: {'section_name': ['keyword1', 'keyword2'], 'global': ['keyword3']}
        """
        print("Scraping UCLouvain course information...")

        if os.path.exists(self.data_folder):
            print(f"Data folder '{self.data_folder}' exists. Loading data from JSON files...")
            all_courses = []
            for filename in os.listdir(self.data_folder):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.data_folder, filename)
                    print(f"Loading courses from program {filepath}")
                    with open(filepath, 'r', encoding='utf-8') as f:
                        courses = json.load(f)
                        all_courses.extend(courses)
            print(len(all_courses), "courses loaded.")
            # Apply filter
            for course_info in all_courses:
                filtered_course = self.filter_course(course_info, **filter_params)
                if filtered_course and course_info['url'] not in self.filtered_course_urls:
                    self.filtered_courses.append(filtered_course)
                    self.filtered_course_urls.add(course_info['url'])
        else:
            print(f"Data folder '{self.data_folder}' doesn't exist. Starting scraping...")
            os.makedirs(self.data_folder)
            programs = self.get_programs()
            total_programs = len(programs)

            for idx, program_url in enumerate(programs, 1):
                progress = (idx / total_programs) * 100
                print(f"Processing program ({idx}/{total_programs}) [{progress:.2f}%]: {program_url}")
                course_links = self.get_course_links(program_url)
                all_courses_for_program = []
                program_code = program_url.split('prog-2024-')[-1]

                for course_link in course_links:
                    print(f'Processing course: {course_link}')
                    course_info = self.get_course_info(course_link)
                    if course_info:
                        all_courses_for_program.append(course_info)

                        # Apply filter
                        filtered_course = self.filter_course(course_info, **filter_params)
                        if filtered_course and course_info['url'] not in self.filtered_course_urls:
                            self.filtered_courses.append(filtered_course)
                            self.filtered_course_urls.add(course_info['url'])

                # Save all courses for a program into a JSON file
                filename = os.path.join(self.data_folder, f"{program_code}.json")
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(all_courses_for_program, f, ensure_ascii=False, indent=4)

        # Save the filtered courses into a JSON file
        with open(self.output_filtered_filename, 'w', encoding='utf-8') as f:
            json.dump(self.filtered_courses, f, ensure_ascii=False, indent=4)
      
        for course in self.filtered_courses:
            print(f"Title: {course['title']}")
            print(f"Credits: {course['credits']}")
            print(f"Quadrimester: {course['quadrimester']}")
            print(f"URL: {course['url']}")
            print(f"Teachers: {', '.join(course.get('teachers', []))}")
            # print(f"Language: {course.get('teaching_language', 'N/A')}")
            # print(f"Topics Covered: {course.get('topics_covered', 'N/A')}")
            # print(f"Learning Outcomes: {course.get('learning_outcomes', 'N/A')}")
            # print(f"Content: {course.get('content', 'N/A')}")
            # print(f"Teaching Methods: {course.get('teaching_methods', 'N/A')}")
            # print(f"Assessment Methods: {course.get('assessment_methods', 'N/A')}")
            # print(f"Other Info: {course.get('other_info', 'N/A')}")
            # print(f"Online Resources: {course.get('online_resources', 'N/A')}")
            print(f"Responsible Entity: {course.get('responsible_entity', 'N/A')}")
            print('=' * 80)

if __name__ == "__main__":
    # Define your filter parameters
    # example include_keywords = {'global': [''], 'teaching_methods': ['']}
    # example exclude_keywords = {'global': [''], 'assessment_methods': ['', '']} 
    
    filter_params = {
        'min_credits': 2,
        'max_credits': 6,
        'quadrimester': ['Q1'], # ['Q1'], ['Q2'], ['Q1', 'Q2'], ['Q1Q2']
        'include_keywords': None,
        'exclude_keywords': None
    }

    base_url = 'https://uclouvain.be/fr/catalogue-formations/masters-2024-par-domaine.html'
    scraper = UCLouvainCourseScraper(base_url, output_filtered_filename='filtered_courses.json')
    scraper.scrape(filter_params)