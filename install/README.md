# Installation Notes

### Environment

The fermentrack_push_target is a Django-based Python script which is designed to be used for testing an upstream 
installation of Fermentrack's push support. The script is *not* designed for use in production environments and does not
support features such as access control which would be necessary for deployment on an externally-accessible server.

To run this script, you need a webserver that is configured to serve pages from a Django-based web application. The
environment used by the author for testing uses:

* Nginx (webserver)
* uwsgi
* Python 3.6

##### uwsgi configuration

uwsgi can generally be configured by following [this tutorial](https://www.digitalocean.com/community/tutorials/how-to-serve-django-applications-with-uwsgi-and-nginx-on-ubuntu-14-04#setting-up-the-uwsgi-application-server).
A sample uwsgi configuration file is located in this directory as fermentrack_push_target.ini

##### nginx configuration

A sample nginx configuration file is located within this directory as nginx_config.conf. The sample configuration runs on port 81 so as to not conflict with an installation of Fermentrack on the same server. 

