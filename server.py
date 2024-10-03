import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse, unquote
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf-8")
            
            # Write your code here
            query = parse_qs(environ["QUERY_STRING"])
            location = query.get("location", [None])[0]
            start_date = query.get("start_date", [None])[0]
            end_date = query.get("end_date", [None])[0]

            final_reviews = reviews

            if location:
                location = unquote(location)
                final_reviews = [review for review in final_reviews if review['Location'] == location]
            

            if start_date:
                 start_date = datetime.strptime(start_date, '%Y-%m-%d')
                 final_reviews = [review for review in final_reviews if datetime.strptime(review['Timestamp'], '%Y-%m-%d %H:%M:%S').date() >= start_date.date()]
                 
            if end_date:
                 end_date = datetime.strptime(end_date, '%Y-%m-%d')
                 final_reviews = [review for review in final_reviews if datetime.strptime(review['Timestamp'], '%Y-%m-%d %H:%M:%S').date() <= end_date.date()]

            
            for review in final_reviews:
                review['sentiment'] = self.analyze_sentiment(review['ReviewBody'])

            final_reviews.sort(key=lambda x: x['sentiment']['compound'], reverse=True)
            
            response_body = json.dumps(final_reviews, indent=2).encode("utf-8")

            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            payload = environ['wsgi.input'].read(content_length).decode('utf-8')
            payload_params = parse_qs(payload)

            review_body = payload_params.get('ReviewBody', [''])[0]
            location = payload_params.get('Location', [''])[0]

            #check for required field(s)
            if not review_body or not location:
                start_response('400 bad request', [("Content-Type", "applicaion/json")])
                return [b"ReviewBody and Location are required!"]
            
            valid_locations = set(review['Location'] for review in reviews)
            if location not in valid_locations:
                start_response('400 Bad Request', [("Content-Type", "application/json")])
                return [json.dumps({"error": "Invalid location"}).encode('utf-8')]

            new_review = {
                "ReviewId": str(uuid.uuid4()),
                "ReviewBody": review_body,
                "Location": location,
                "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            reviews.append(new_review)

            response_body = json.dumps(new_review, indent=2).encode('utf-8')

            start_response("201 OK", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
            ])
            
            return [response_body]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()