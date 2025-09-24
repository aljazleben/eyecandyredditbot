import os
import json
from datetime import datetime, timedelta, timezone
import praw
from prawcore.exceptions import PrawcoreException, OAuthException, ResponseException


CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")

if not CLIENT_ID or not CLIENT_SECRET or not USER_AGENT:
    raise RuntimeError(
        "Missing Reddit credentials. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT."
    )

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT,
)
reddit.read_only = True


def _title_matches(submission, keywords_lower: list) -> bool:
    if not keywords_lower:
        return True
    try:
        title = (submission.title or "").lower()
        return any(keyword in title for keyword in keywords_lower)
    except Exception:
        return False


def get_account_details(username: str, period_days: int = 1):
    try:
        user = reddit.redditor(username)
        account_age = datetime.now(timezone.utc) - datetime.fromtimestamp(
            user.created_utc, timezone.utc
        )
        account_age_days = account_age.days
        post_karma = user.link_karma
        comment_karma = user.comment_karma

        now = datetime.now(timezone.utc)
        period_ago = now - timedelta(days=period_days)

        deleted_posts = 0
        removed_by_mods = 0
        removed_by_spam = 0
        removed_by_rules = 0
        posts_submitted = 0
        total_upvotes = 0
        total_comments = 0

        highest_posts = []
        removed_posts_links = []

        for submission in user.submissions.new(limit=None):
            submission_time = datetime.fromtimestamp(
                submission.created_utc, timezone.utc
            )
            if submission_time > period_ago:
                posts_submitted += 1
                total_upvotes += submission.score
                total_comments += submission.num_comments
                highest_posts.append(
                    {
                        "title": submission.title,
                        "upvotes": submission.score,
                        "subreddit": submission.subreddit.display_name,
                        "permalink": submission.permalink,
                    }
                )
                if submission.removed_by_category is not None:
                    deleted_posts += 1
                    if submission.removed_by_category == "moderator":
                        removed_by_mods += 1
                    elif submission.removed_by_category == "spam":
                        removed_by_spam += 1
                    elif submission.removed_by_category == "subreddit":
                        removed_by_rules += 1
                    removed_posts_links.append(
                        {
                            "title": submission.title,
                            "subreddit": submission.subreddit.display_name,
                            "link": f"https://www.reddit.com{submission.permalink}",
                        }
                    )

        highest_posts.sort(key=lambda x: x["upvotes"], reverse=True)

        data = {
            "username": username,
            "period_days": period_days,
            "account_age_days": account_age_days,
            "post_karma": post_karma,
            "comment_karma": comment_karma,
            "posts_submitted": posts_submitted,
            "deleted_posts": deleted_posts,
            "removed_by_mods": removed_by_mods,
            "removed_by_spam": removed_by_spam,
            "removed_by_rules": removed_by_rules,
            "total_upvotes": total_upvotes,
            "total_comments": total_comments,
            "highest_posts": highest_posts[:5],
            "removed_posts_links": removed_posts_links,
        }
        return json.dumps(data)

    except (PrawcoreException, OAuthException, ResponseException) as e:
        raise RuntimeError(f"Reddit API error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")


def get_top_30_captions(
    username: str, keywords: str = "", limit: int = 30, captions_only: bool = False
):
    try:
        user = reddit.redditor(username)
        keywords_lower = [
            keyword.strip().lower() for keyword in keywords.split(",") if keyword.strip()
        ]
        results = []

        if keywords_lower:
            for submission in user.submissions.top(limit=None):
                if _title_matches(submission, keywords_lower):
                    results.append(
                        {
                            "title": submission.title,
                            "upvotes": submission.score,
                            "subreddit": submission.subreddit.display_name,
                            "permalink": submission.permalink,
                        }
                    )
                    if len(results) >= limit:
                        break
        else:
            for submission in user.submissions.top(limit=limit):
                results.append(
                    {
                        "title": submission.title,
                        "upvotes": submission.score,
                        "subreddit": submission.subreddit.display_name,
                        "permalink": submission.permalink,
                    }
                )

        data = {
            "username": username,
            "keywords": keywords,
            "limit": limit,
            "captions_only": captions_only,
            "results": results,
        }
        return json.dumps(data)

    except (PrawcoreException, OAuthException, ResponseException) as e:
        raise RuntimeError(f"Reddit API error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")


def get_top_20_hot(
    subreddit_name: str, keywords: str = "", limit: int = 20, captions_only: bool = False
):
    try:
        subreddit = reddit.subreddit(subreddit_name)
        keywords_lower = [
            keyword.strip().lower() for keyword in keywords.split(",") if keyword.strip()
        ]
        results = []

        if keywords_lower:
            for submission in subreddit.hot(limit=None):
                if _title_matches(submission, keywords_lower):
                    results.append(
                        {
                            "title": submission.title,
                            "upvotes": submission.score,
                            "permalink": submission.permalink,
                        }
                    )
                    if len(results) >= limit:
                        break
        else:
            for submission in subreddit.hot(limit=limit):
                results.append(
                    {
                        "title": submission.title,
                        "upvotes": submission.score,
                        "permalink": submission.permalink,
                    }
                )

        data = {
            "subreddit": subreddit_name,
            "keywords": keywords,
            "limit": limit,
            "captions_only": captions_only,
            "results": results,
        }
        return json.dumps(data)

    except (PrawcoreException, OAuthException, ResponseException) as e:
        raise RuntimeError(f"Reddit API error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")


def get_top_20_all_time(
    subreddit_name: str, keywords: str = "", limit: int = 20, captions_only: bool = False
):
    try:
        subreddit = reddit.subreddit(subreddit_name)
        keywords_lower = [
            keyword.strip().lower() for keyword in keywords.split(",") if keyword.strip()
        ]
        results = []

        if keywords_lower:
            for submission in subreddit.top(limit=None):
                if _title_matches(submission, keywords_lower):
                    results.append(
                        {
                            "title": submission.title,
                            "upvotes": submission.score,
                            "permalink": submission.permalink,
                        }
                    )
                    if len(results) >= limit:
                        break
        else:
            for submission in subreddit.top(limit=limit):
                results.append(
                    {
                        "title": submission.title,
                        "upvotes": submission.score,
                        "permalink": submission.permalink,
                    }
                )

        data = {
            "subreddit": subreddit_name,
            "keywords": keywords,
            "limit": limit,
            "captions_only": captions_only,
            "results": results,
        }
        return json.dumps(data)

    except (PrawcoreException, OAuthException, ResponseException) as e:
        raise RuntimeError(f"Reddit API error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")


