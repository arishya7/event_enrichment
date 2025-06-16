blog_ls = open('blog_websites.txt', 'r').read()
print(blog_ls)
print([blog.split(',')[1] for blog in blog_ls.split('\n')])