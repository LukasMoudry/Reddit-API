import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import praw
import webbrowser
import threading

# Load Reddit API credentials from a text file
# The file should have three lines: client_id, client_secret, and user_agent.
with open("credentials.txt", "r") as f:
    lines = f.readlines()
client_id = lines[0].strip()
client_secret = lines[1].strip()
user_agent = lines[2].strip()

# Reddit API Authentication (read-only mode)
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    user_agent=user_agent
)

class RedditApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reddit Viewer")
        self.root.configure(bg="#dae0e6")  # Reddit-like light background

        # Options frame for feed and sort selections
        options_frame = ttk.Frame(root)
        options_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        # Feed selection: Home vs. Popular
        self.feed_var = tk.StringVar(value="Home")
        ttk.Label(options_frame, text="Feed:").pack(side=tk.LEFT, padx=(0, 5))
        feed_menu = ttk.OptionMenu(options_frame, self.feed_var, "Home", "Home", "Popular")
        feed_menu.pack(side=tk.LEFT, padx=(0, 15))

        # Sort selection: Hot, Best, New, Top, Rising
        self.sort_var = tk.StringVar(value="Hot")
        ttk.Label(options_frame, text="Sort:").pack(side=tk.LEFT, padx=(0, 5))
        sort_menu = ttk.OptionMenu(options_frame, self.sort_var, "Hot", "Hot", "Best", "New", "Top", "Rising")
        sort_menu.pack(side=tk.LEFT, padx=(0, 15))

        # Refresh button to fetch posts based on selections
        refresh_button = ttk.Button(options_frame, text="Refresh", command=self.refresh_posts)
        refresh_button.pack(side=tk.LEFT, padx=(0, 15))

        # Frame for displaying posts (left side)
        self.post_frame = ttk.Frame(root)
        self.post_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame for displaying post details and comments (right side)
        self.comment_frame = ttk.Frame(root)
        self.comment_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Listbox to show Reddit posts
        self.post_listbox = tk.Listbox(self.post_frame, height=20, width=50, font=("Arial", 10))
        self.post_listbox.pack(fill=tk.BOTH, expand=True)
        self.post_listbox.bind('<<ListboxSelect>>', self.on_post_select)

        # ScrolledText widget to show post details, content, and comments
        self.comment_text = ScrolledText(self.comment_frame, height=20, width=60, font=("Arial", 10))
        self.comment_text.pack(fill=tk.BOTH, expand=True)

        # Button to open the selected post in a browser
        self.open_url_button = ttk.Button(self.comment_frame, text="Open Post in Browser", command=self.open_url)
        self.open_url_button.pack(pady=5)

        self.posts = []
        self.selected_post_url = None

        # Initially fetch posts
        self.refresh_posts()

    def refresh_posts(self):
        # Clear posts and comment text before reloading
        self.post_listbox.delete(0, tk.END)
        self.comment_text.delete(1.0, tk.END)
        self.post_listbox.insert(tk.END, "Loading posts...")
        # Fetch posts in a separate thread to avoid freezing the UI
        threading.Thread(target=self.fetch_posts, daemon=True).start()

    def fetch_posts(self):
        feed = self.feed_var.get()
        sort = self.sort_var.get().lower()  # e.g., "hot", "best", etc.
        try:
            if feed == "Home":
                # In read-only mode, Home may not be personalized.
                posts = getattr(reddit.front, sort)(limit=20)
            else:  # Popular feed
                posts = getattr(reddit.subreddit("popular"), sort)(limit=20)
            self.posts = list(posts)
        except Exception as e:
            self.posts = []
            error_message = f"Error fetching posts: {e}"
            self.root.after(0, lambda: self.show_error(error_message))
            return
        self.root.after(0, self.update_post_listbox)

    def update_post_listbox(self):
        self.post_listbox.delete(0, tk.END)
        if not self.posts:
            self.post_listbox.insert(tk.END, "No posts found.")
        else:
            for i, post in enumerate(self.posts):
                self.post_listbox.insert(tk.END, f"{i+1}. {post.title} (Score: {post.score})")

    def show_error(self, message):
        self.post_listbox.delete(0, tk.END)
        self.post_listbox.insert(tk.END, message)

    def on_post_select(self, event):
        if not self.post_listbox.curselection():
            return
        selected_index = self.post_listbox.curselection()[0]
        if selected_index >= len(self.posts):
            return  # Prevent index error if the listbox shows a placeholder message
        selected_post = self.posts[selected_index]
        self.selected_post_url = selected_post.url  # Save URL for browser opening

        self.comment_text.delete(1.0, tk.END)
        self.comment_text.insert(tk.END, "Loading post details and comments...\n")
        threading.Thread(target=self.fetch_comments, args=(selected_post,), daemon=True).start()

    def fetch_comments(self, post):
        try:
            post.comments.replace_more(limit=0)
            comments = post.comments.list()[:10]  # Get the top 10 comments
        except Exception as e:
            error_message = f"Error fetching comments: {e}"
            self.root.after(0, lambda: self.display_post(post, [], error_message))
            return
        self.root.after(0, lambda: self.display_post(post, comments))

    def display_post(self, post, comments, error=None):
        self.comment_text.delete(1.0, tk.END)
        if error:
            self.comment_text.insert(tk.END, error)
            return
        # Display post details
        self.comment_text.insert(tk.END, f"Title: {post.title}\n", "title")
        self.comment_text.insert(tk.END, f"Score: {post.score}\n", "score")
        self.comment_text.insert(tk.END, f"URL: {post.url}\n\n", "url")
        # Display post content if available (for self-posts)
        if post.selftext:
            self.comment_text.insert(tk.END, f"Content:\n{post.selftext}\n\n", "content")
        # Display comments header and comments
        self.comment_text.insert(tk.END, "Comments:\n", "header")
        for comment in comments:
            self.comment_text.insert(tk.END, f"- {comment.body}\n\n", "comment")

    def open_url(self):
        """Opens the selected post's URL in the default browser."""
        if self.selected_post_url:
            webbrowser.open(self.selected_post_url)

def apply_text_styles(widget):
    widget.tag_config("title", font=("Arial", 12, "bold"), foreground="#1a0dab")
    widget.tag_config("score", font=("Arial", 10, "bold"), foreground="#ff4500")
    widget.tag_config("url", font=("Arial", 10, "italic"), foreground="blue")
    widget.tag_config("header", font=("Arial", 12, "bold"))
    widget.tag_config("content", font=("Arial", 10), foreground="#000000")
    widget.tag_config("comment", font=("Arial", 10), foreground="#000000")

# Initialize the Tkinter app
root = tk.Tk()
app = RedditApp(root)
apply_text_styles(app.comment_text)
root.mainloop()
