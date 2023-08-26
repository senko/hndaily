# Hacker News Daily

A digest newsletter for top Hacker News stories. Can be run daily (hence the name),
weekly, or at any other interval.

The newsletter uses the official HN API to fetch the top stories  and
creates an email with the stories in HTML format. The email is sent to the
recipient address.

For each story, only the title, number of comments, number of points, and
links to the web and HN discussion are included.

Hacker News Daily is **NOT** affiliated with or endorsed by HN or YC.

## Installation

Hacker News Daily requires Python 3.9+.

Clone the repository:

    git clone git@github.com:senko/hndaily.git
    cd hndaily/

Set up and activate a new Python virtual environment:

    python -m venv .venv
    source .venv/bin/activate

Install the dependencies:

    pip install -r requirements.txt

Configure the environment variables:

    cp env.sample .env
    vim .env

Run the script:

    python src/digest.py

## License

Hacker News Daily is licensed under the MIT license. See the `LICENSE` file for details.
