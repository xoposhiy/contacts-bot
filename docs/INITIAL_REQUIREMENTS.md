# Telegram Bot for Student Contacts – Specification

## Core function

* The bot provides information about students in the specific university programs.
* A user sends the bot a student’s first name, last name, or one of their known names.
* If the bot identifies a single student confidently, it returns that student’s card.
* If the bot is uncertain which student is intended, it returns a list of matching students.
* The user can then select a name from the list and make a more specific request.

## Access control

* Access to the bot is restricted.
* Only a specified list of people may use it.
* Allowed users are defined by their Telegram handles and/or Telegram IDs and stored in the firestore collection 'users'

## Technology stack

* All student data is stored in Firestore collection 'contacts'
* The initial source of information is Google Sheets tables.
* The bot is implemented in Python.
* Firestore Emulator is used for testing.
* Deployment is handled via Code.Run on Google Cloud.

---

## Architecture

* Each feature lives in its own folder (feature-oriented structure).
* 
* In each feature folder:
  * Database logic is implemented in a service class.
  * The service class receives a Firebase client as a dependency.
  * Telegram command handlers are defined in a separate file. All complex message and buttons rendering logic goes to the separate functions.
* Common infrastructure not related to any particular feature is implemented in a separate folder 'common'
* Never create services and clients in the command handlers — receive them as a depencencies.
* Use dependency injection to pass the client to the service. Setup the dependencies in the main.py
---

## Unit testing strategy

* Place tests in the feature folders.
* Each feature must have its own unit tests.
* Tests run against the Firestore Emulator.
* Tests interact through the command interface.
* Tests do not use the Telegram API or runtime.
* There is a code to create a small test database. This code can be used to run tests locally.


---

## Features

### 1. Search

* Any incoming text first is interpreted as a name query (no explicit command).
* Each student can have multiple given names; search matches against any of these names.
* If the query uniquely identifies a single student, return that student’s card.
* If multiple students match, return a candidate list formatted for one-click name copy.

**Data model requirements (from Google Sheets):**

* Names: all given names/aliases, and family name.
* Admission year.
* Is a scholarship student
* Public comment (optional).
* Secret comment (optional).
* Contacts: emails, Telegram handle.
* Personal data: citizenship/nationality/country of origin.
* Academic data: courses taken, courses registered for, and grades.

By default, fields are considered 'additional' and are not shown in the card.

Firestore collection 'fields' contains a list of field names with status:
* Primary: shown in the card by default.
* Courses
* Others
Also for each field store the list of sinonym names (how they may be called in the sheet).


**Contact's card:**

* Show primary fields: name, contacts, admission year, scholarship.
* Student card includes buttons: Courses and Others.
  * “Courses” → shows course registrations and grades.
  * “Other” → shows additional data (may be regrouped later).


### 2. Import students

* Source is a CSV file.
* When you send csv file to bot it will be imported into database.
* The bot loads all rows from the csv.

**Matching rules:**

* A student is identified if *any one* of these match (in this order):
  * Any Email
  * Telegram handle
  * All names from the query contains in the set of Given names + family name
* If no existing student matches, create a new student record.
* If several matching students exists, ignore and report.

**Field mapping & updates:**

* Use database field names as sheet column headers.
* Save all provided fields into the database.
* Count as “updated” only if at least one field value changes.

**Duplicates:**

* Detect when multiple sheet rows match the same student. Update but report.
* For every duplicate group:
  * Report explicitly in post-import summary.
  * Apply updates from each row sequentially; later ones may overwrite earlier ones.

**Post-import reporting:**

* Number of newly created students.
* Number of updated students.
* Number and details of duplicate rows/groups, including applied overwrites.


## Firestore Data model

### 'students' collection

Fields:
  * name
  * family_name
  * cub_email
  * personal_email
  * telegram_handle
  * admission_year
  * scholarship
  * country
  * public_comment
  * secret_comment
  * courses
    * name
    * grade
  * ...
    
### 'fields' collection

Fields:
  * name
  * type: primary | courses | others
  * synonyms: []
  * aliases: []

### 'users' collection

Fields:
  * telegram_id
  * telegram_handle
  * role: admin | user

