# hack-challenge
Repository for 2022 Hack Challenge

APP NAME: Side Quest

TAGLINE: App for students to make easy money by connecting them to organizations/people offering rewards for gigs, research participation, surveys, etc.

Our app is a gig based app which students in Cornell will use to make money through completing one time tasks. At Cornell many organizations offer money, credit, or other compensation for students participating in tasks such as postering, taking part in research, surveying, or providing entertainment. Our app provides a space for people to post listing, and for others to take these listings in exchange for compensation.

Our backend database features 6 classes: User, Asset, Job, Rating, Chat, and Message. All classes have at least one get all, create, update, get by id, and delete.

The User class contains information relating to logging into the app and information relating to a person's profile. We fulfilled the requirement of having authentication with this class.

The Asset classes implements images, which gives the user the ability to add a profile picture. 

The Job class contains information for each jobs and has four extra api routes. One for the filtering the job result with a search condition, one for users to add jobs they want to do, one for job posters to pick someone to do their job and one for users to tell the job poster that the job is done.

The Rating class contains rating information and allows users to rate other users.

The Chat class stores message informations and all the users in that chat.

The Message class contains information on the person who sent the message and the message.

Relationships and Tables:
    User and Assets: One to many
    User and Job: Many to many
    User and Rating: Many to many
    User and Chat: Many to many
    User and Message: One to many
    Job and Asset: One to Many

EXTERNAL API USE:

    We used SocketIO in our backend to allow messaging between users. Instead of updating whenever a request is sent, it listens for events. SocketIO interacted with out Chat and Message routes.

    We used SendGridApi to send emails whenever a user registers, a user is chosen for a side quest, and when a job is done.




