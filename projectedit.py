import os
import webapp2
import jinja2
import hashlib
import hmac
import random
import re
import string
from jinja2 import filters, environment
#from string import letters
from google.appengine.ext import db

#from dbmodel import Users
from dbmodel import Comments
from dbmodel import Likes

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)


# create a flter to get comments for a post
def getcomments(post_id):
    coms = db.GqlQuery("select * from Comments where post_id=" + post_id +
                       " order by created desc")
    return coms;

#Register the filter with Environment
#jinja_env.filters['getusername'] = getusername
#jinja_env.filters['getcomments'] = getcomments

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

# Module contains all storage tables
class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created_by = db.IntegerProperty(required = True)
    count_like = db.IntegerProperty(default=0)
    count_comment = db.IntegerProperty(default=0)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

#    def render(self, user):
#        self._render_text = self.content.replace('\n', '<br>')
#        return render_str("post.html", p = self, u=user)
#       t = jinja_env.get_template("post.html")
#       return t.render(p = self, u=user)        

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

def render_post(response, post):
        response.out.write('<b>' + post.subject + '</b><br>')
        response.out.write(post.content)

class MainPage(BlogHandler):
  def get(self):
      self.write('Project')

##### blog stuff

def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)         

#Posting a page leads to a perma link.
class PostPage(webapp2.RequestHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

# Check if user is logged in, if not redirect to login.
# Modify to user both new post and edit existing post
class NewPost(webapp2.RequestHandler):
    def get(self, post_id):
        user=None
        post=None
        # Can't handle zero - throws excption
        if int(post_id) > 0 :
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
                 

    def post(self, p_id):
        # Validate user
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        user =None
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;
        if user:
            #post_id = self.request.get('post_id')
            subject = self.request.get('subject')
            content = self.request.get('content')
            post = None
            # if post_id is valid - this is an edit
            if int(p_id) > 0:
                # Handle failure- in case if a invalid key is provided.
                key = db.Key.from_path('Post', int(p_id), parent=blog_key())
                if key:
                    post = db.get(key)                        

            if subject and content:
                if post:
                    post.subject = subject
                    post.content = content
                    post.put()
                else:
                    post = Post(parent = blog_key(), subject = subject, 
                         content = content, created_by=uid)
                    post.put()
                self.redirect('/blog/%s' % str(post.key().id()))
            else: # if updated with blank subject
                error = "subject and content, please!"
                #self.render("newpost.html", post_id=post_id, subject=subject, 
                #            content=content, error=error, u = user)
                t = jinja_env.get_template('newpost.html')
                self.response.out.write(t.render(p=post, u=user))
                
        else:
            self.redirect('/blog/login')
# Global function - all comments and likes with post.
def deletePost(post_id):
    if int(post_id) > 0 :
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        if post:
            coms = db.GqlQuery(
             "SELECT * FROM Comments WHERE post_id=" + str(post.key().id()))
            for c in coms:
                c.delete()
            likes = db.GqlQuery(
             "SELECT * FROM Likes WHERE post_id=" + str(post.key().id()))
            for l in likes:
                l.delete()
            post.delete()
            
            
# Check if user is logged in, if not redirect to login.
# Delete post, comments and likes
class DelPost(webapp2.RequestHandler):
    def get(self, post_id):
        user=None
        post=None
        if int(post_id) > 0 :
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
        if post:
             deletePost(post.key().id())
        
        self.redirect('/blog')        

class DelComment(webapp2.RequestHandler):
    def get(self, comment_id):
        user=None
        comment=None
        post_id = None
        if int(comment_id) > 0 :         
            key = db.Key.from_path('Comments', int(comment_id), parent=blog_key())
            comment = db.get(key)

        if comment:
                comment.delete()
                pkey = db.Key.from_path('Post', int(post_id), parent=blog_key())
                post = db.get(pkey)
                post.count_comment -= 1
                post.put()
                
        if post_id :
            self.redirect('/blog/comment/' + str(post_id))
        else :
            self.redirect('/blog')
        
# Check if user is logged in, if not redirect to login.
class CommentPost(webapp2.RequestHandler):
    def get(self, post_id):
        user = None
        if uid != 0:
            user = Users.get_by_id(uid)
        if user:
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)                        
            if post:
                coms = getcomments(post_id)
                t = jinja_env.get_template('comment.html')
                #self.render('comment.html', post=post, coms=coms, u = user)
                self.response.out.write(t.render(post=post, coms=coms, u=user))     

    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        user = None
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;
        if user :
            comment = self.request.get('comment')
            # User can't comment his own blog            
            if comment and post.created_by != uid :
                com = Comments(parent = blog_key(), 
                         post_id = int(post_id), 
                         user_id=uid, comment = comment)
                com.put()
                if post: 
                    post.count_comment += 1;
                    post.put()
                # Find and update post id as well
                self.redirect('/blog/%s' % str(post.key().id()))
            else:
                error = "comment, please!"
                coms = getcomments(post_id)
                t = jinja_env.get_template('comment.html')
                self.response.out.write(t.render(posts=posts, coms=coms, u=user))
                #self.render("comment.html", posts=posts,coms=coms,u = user)

# Check if user is logged in, if not redirect to login.
class EditComment(webapp2.RequestHandler):
    def get(self, comment_id):
        user = None
        if user and int(comment_id) > 0:
            ckey = db.Key.from_path('Comments', int(comment_id), parent=blog_key())
            com = db.get(ckey)        
            if com:
                pkey = db.Key.from_path('Post', int(com.post_id), parent=blog_key())
                post = db.get(pkey)
                t = jinja_env.get_template('comment-edit.html')
                #self.render('comment.html', post=post, coms=coms, u = user)
                self.response.out.write(t.render(post=post, com=com, u=user))   

    def post(self, com_id):
        ckey = db.Key.from_path('Comments', int(com_id), parent=blog_key())
        com = db.get(ckey)
        user = None
        if user :
            updated_comment = self.request.get('comment')
            # User can update his own comment
            if updated_comment and com.user_id == uid :
                com.comment = updated_comment
                com.put()
                self.redirect('/blog/comment/%s' % str(com.post_id))
            else:
                # empty comment - lan to same page
                self.redirect('/blog/editcom/%s' % str(com.key().id()))

    def get(self):
        #Get user name from cookie
        uid_cookie_str = self.request.cookies.get('uid')
        uid = check_secure_val(uid_cookie_str);
        user =""
        if uid != 0:
            user = Users.get_by_id(uid)
            username = user.username;

        if user:
            self.render('welcome.html', u = user)
        else:
            self.redirect('/blog/signup')
            

app = webapp2.WSGIApplication([
       ('/', MainPage),
       ('/blog/([0-9]+)', PostPage),
       ('/blog/newpost/([0-9]+)', NewPost),
       ('/blog/delpost/([0-9]+)', DelPost),
       ('/blog/delcom/([0-9]+)', DelComment),
       ('/blog/editcom/([0-9]+)', EditComment),
       ('/blog/comment/([0-9]+)', CommentPost), # post_id as a param      
       ],
      debug=True)