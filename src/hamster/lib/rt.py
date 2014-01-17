"""
======================================================
 Rt - Python interface to Request Tracker :term:`API`
======================================================

Description of Request Tracker :term:`REST` :term:`API`:
http://requesttracker.wikia.com/wiki/REST

Provided functionality:

* login to RT
* logout
* getting, creating and editing tickets
* getting attachments
* getting history of ticket
* replying to ticket requestors
* adding comments
* getting and editing ticket links
* searching
* providing lists of last updated tickets
* providing tickets with new correspondence
* merging tickets
"""

__license__ = """ Copyright (C) 2012 CZ.NIC, z.s.p.o.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
__docformat__ = "reStructuredText en"
__authors__ = [
  '"Jiri Machalek" <jiri.machalek@nic.cz>'
]

import re
import os
import requests
import logging
from beaker.cache import cache_regions, cache_region

# configure regions
cache_regions.update({
    'short_term':{
        'expire': 60,
        'type': 'memory',
        'key_length': 250
    }
})

DEFAULT_QUEUE = 'General'
""" Default queue used. """

TICKET_NAME_REGEX = "^#(\d+): "

TIMEOUT = 5# seconds

class Rt:
    """ :term:`API` for Request Tracker according to
    http://requesttracker.wikia.com/wiki/REST. Interface is based on
    :term:`REST` architecture, which is based on HTTP/1.1 protocol. This module
    is therefore mainly sending and parsing special HTTP messages.
    
    .. note:: Use only ASCII LF as newline (``\\n``). Time is returned in UTC.
              All strings returned are encoded in UTF-8 and the same is
              expected as input for string values.
    """

    def __init__(self, url, default_login=None, default_password=None, proxy=None):
        """ API initialization.
        
        :keyword url: Base URL for Request Tracker API.
                      E.g.: http://tracker.example.com/REST/1.0/
        :keyword default_login: Default RT login used by self.login if no
                                other credentials are provided
        :keyword default_password: Default RT password
        :keyword proxy: Proxy server (string with http://user:password@host/ syntax)
        """
        self.url = url
        self.default_login = default_login
        self.default_password = default_password
        if proxy is not None:
            if url.lower().startswith("https://"):
                proxy = {"https": proxy}
            else:
                proxy = {"http": proxy}
        self.session = requests.session()
        self.login_result = None

    def __request(self, selector, post_data={}, files=[], without_login=False, timeout=None):
        """ General request for :term:`API`.
 
        :keyword selector: End part of URL which completes self.url parameter
                           set during class inicialization.
                           E.g.: ``ticket/123456/show``
        :keyword post_data: Dictionary with POST method fields
        :keyword files: List of pairs (filename, file-like object) describing
                        files to attach as multipart/form-data
                        (list is necessary to keep files ordered)
        :keyword without_login: Turns off checking last login result
                                (usually needed just for login itself)
        :returns: Requested messsage including state line in form
                  ``RT/3.8.7 200 Ok\\n``
        :rtype: string
        :raises Exception: In case that request is called without previous
                           login or any other connection error.
        """
        timeout=timeout or TIMEOUT
        try:
            url = str(os.path.join(self.url, selector))
            if self.login_result or without_login:
                if not files:
                    if post_data:
                        response = self.session.post(url, data=post_data, timeout=timeout)
                    else:
                        response = self.session.get(url, timeout=timeout)
                else:
                    files_data = {}
                    for i in range(len(files)):
                        files_data['attachment_%d' % (i+1)] = files[i]
                    response = self.session.post(url, data=post_data, files=files_data, timeout=TIMEOUT)
                if isinstance(response.content, bytes):
                    return bytes.decode(response.content)
                else:
                    return response.content
            else:
                raise Exception('Log in required')
        except requests.exceptions.ConnectionError as e:
            raise Exception(e.args[0].message)
    
    def __get_status_code(self, msg):
        """ Select status code given message.

        :returns: Status code
        :rtype: int
        """
        return int(msg.split('\n')[0].split(' ')[1])

    def login(self, login=None, password=None):
        """ Login with default or supplied credetials.
        
        :keyword login: Username used for RT, if not supplied together with
                        *password* :py:attr:`~Rt.default_login` and
                        :py:attr:`~Rt.default_password` are used instead
        :keyword password: Similarly as *login*
        
        :returns: ``True``
                      Successful login
                  ``False``
                      Otherwise
        :raises Exception: In case that credentials are not supplied neither
                           during inicialization or call of this method.
        """

        if (login is not None) and (password is not None):
            login_data = {'user':login, 'pass':password}
        elif (self.default_login is not None) and (self.default_password is not None):
            login_data = {'user':self.default_login, 'pass':self.default_password}
        else:
            raise Exception('Credentials required')

        self.login_result = self.__get_status_code(self.__request('',
                                                                  post_data=login_data,
                                                                  without_login=True)) == 200
        return self.login_result

    def logout(self):
        """ Logout of user.
        
        :returns: ``True``
                      Successful logout
                  ``False``
                      Logout failed (mainly because user was not login)
        """
        ret = False
        if self.login_result == True:
            ret = self.__get_status_code(self.__request('logout')) == 200
            self.login_result = None
        return ret
        
    def new_correspondence(self, queue=DEFAULT_QUEUE):
        """ Obtains tickets changed by other users than the system one.
        
        :keyword queue: Queue where to search
        
        :returns: List of tickets which were last updated by other user than
                  the system one ordered in decreasing order by LastUpdated.
                  Each ticket is dictionary, the same as in
                  :py:meth:`~Rt.get_ticket`.
        """
        items = []
        try:
            msgs = self.__request('search/ticket?query=Queue=\'%s\'+AND+(LastUpdatedBy!=\'%s\')&orderby=-LastUpdated&format=l' % (queue, self.default_login))
            msgs = msgs.split('\n--\n')
            for i in range(len(msgs)):
                pairs = {}
                msg = msgs[i].split('\n')
                for i in range(len(msg)):
                    colon = msg[i].find(': ')
                    if colon > 0:
                        pairs[msg[i][:colon].strip()] = msg[i][colon+1:].strip()
                if len(pairs) > 0:
                    items.append(pairs)    
            return items
        except:
            return []
        
    def last_updated(self, since, queue=DEFAULT_QUEUE):
        """ Obtains tickets changed after given date.
        
        :param since: Date as string in form '2011-02-24'
        :keyword queue: Queue where to search
        
        :returns: List of tickets with LastUpdated parameter later than
                  *since* ordered in decreasing order by LastUpdated.
                  Each tickets is dictionary, the same as in
                  :py:meth:`~Rt.get_ticket`.
        """
        items = []
        try:
            msgs = self.__request('search/ticket?query=(Queue=\'%s\')+AND+(LastUpdatedBy!=\'%s\')+AND+(LastUpdated>\'%s\')&orderby=-LastUpdated&format=l' % (queue, self.default_login, since))
            msgs = msgs.split('\n--\n')
            for i in range(len(msgs)):
                pairs = {}
                msg = msgs[i].split('\n')
                for i in range(len(msg)):
                    colon = msg[i].find(': ')
                    if colon > 0:
                        pairs[msg[i][:colon].strip()] = msg[i][colon+1:].strip()
                if len(pairs)>0:
                    items.append(pairs)    
            return items
        except:
            return []
    
    def search(self, Queue=DEFAULT_QUEUE, **kwargs):
        """ Search arbitrary needles in given fields and queue.
        
        Example::
            
            >>> tracker = Rt('http://tracker.example.com/REST/1.0/', 'rt-username', 'top-secret')
            >>> tracker.login()
            >>> tickets = tracker.search(CF_Domain='example.com')

        :keyword Queue: Queue where to search
        :keyword kwargs: Other arguments possible to set:
                         
                         Requestors, Subject, Cc, AdminCc, Owner, Status,
                         Priority, InitialPriority, FinalPriority,
                         TimeEstimated, Starts, Due, Text,... (according to RT
                         fields)

                         Setting value for this arguments constrain search
                         results for only tickets exactly matching all
                         arguments.

                         Custom fields CF.{<CustomFieldName>} could be set
                         with keywords CF_CustomFieldName.
        
        :returns: List of matching tickets. Each ticket is the same dictionary
                  as in :py:meth:`~Rt.get_ticket`.
        :raises Exception: Unexpected format of returned message.
        """
        query = '(Queue=\'%s\')' % (Queue,)
        for key in kwargs:
            if key[:3] != 'CF_':
                query += "+AND+(%s=\'%s\')" % (key, kwargs[key])
            else:
                query += "+AND+(CF.{%s}=\'%s\')" % (key[3:], kwargs[key])
        return search_raw(query)

    @cache_region('short_term', 'search_simple')
    def search_simple(self, user_query):
        logging.debug('searching')
        query = 'search/ticket?query=' + user_query + "&format=s"
        try:
            msgs = self.__request(query)
            msgs = msgs.split('\n')
            items = []
            for line in msgs:
                if ': ' in line:
                    pairs = {}
                    msg = line.split(': ', 1)
                    pairs['id'] = msg[0]
                    pairs['Subject'] = msg[1]
                    items.append(pairs)
            return items
        except:
            return []

    @cache_region('short_term', 'search_raw')
    def search_raw(self, user_query, additional_fields=[]):
        query = 'search/ticket?query=' + user_query + "&format=l&fields=id,Subject,Owner,Requestors"
        if additional_fields:
            query = ','.join([query]+additional_fields)
        items = []
        try:
            msgs = self.__request(query)
            msgs = msgs.split('\n--\n')
            if not hasattr(self, 'requestors_pattern'):
                self.requestors_pattern = re.compile('Requestors:')
            for i in range(len(msgs)):
                pairs = {}
                msg = msgs[i].split('\n')

                req_id = [id for id in range(len(msg)) if self.requestors_pattern.match(msg[id]) is not None]
                if len(req_id)==0:
                    raise Exception('Non standard ticket.')
                else:
                    req_id = req_id[0]
                for i in range(req_id):
                    colon = msg[i].find(': ')
                    if colon > 0:
                        pairs[msg[i][:colon].strip()] = msg[i][colon+1:].strip()
                requestors = [msg[req_id][12:]]
                req_id += 1
                while (req_id < len(msg)) and (msg[req_id][:12] == ' '*12):
                    requestors.append(msg[req_id][12:])
                    req_id += 1
                pairs['Requestors'] = requestors
                for i in range(req_id,len(msg)):
                    colon = msg[i].find(': ')
                    if colon > 0:
                        pairs[msg[i][:colon].strip()] = msg[i][colon+1:].strip()
                if len(pairs) > 0:
                    items.append(pairs)    
            return items
        except:
            return []

    @cache_region('short_term', 'get_ticket')
    def get_ticket(self, ticket_id):
        """ Fetch ticket by its ID.
        
        :param ticket_id: ID of demanded ticket
        
        :returns: Dictionary with key, value pairs for ticket with
                  *ticket_id*. List of keys:
                  
                      * id
                      * Queue
                      * Owner
                      * Creator
                      * Subject
                      * Status
                      * Priority
                      * InitialPriority
                      * FinalPriority
                      * Requestors
                      * Cc
                      * AdminCc
                      * Created
                      * Starts
                      * Started
                      * Due
                      * Resolved
                      * Told
                      * TimeEstimated
                      * TimeWorked
                      * TimeLeft
        :raises Exception: Unexpected format of returned message.
        """
        msg = self.__request('ticket/%s/show' % (str(ticket_id),))
        if(self.__get_status_code(msg) == 200):
            pairs = {}
            msg = msg.split('\n')

            if not hasattr(self, 'requestors_pattern'):
                self.requestors_pattern = re.compile('Requestors:')
            req_id = [id for id in range(len(msg)) if self.requestors_pattern.match(msg[id]) is not None]
            if len(req_id)==0:
                raise Exception('Non standard ticket.')
            else:
                req_id = req_id[0]
            for i in range(req_id):
                colon = msg[i].find(': ')
                if colon > 0:
                    pairs[msg[i][:colon].strip()] = msg[i][colon+1:].strip()
            requestors = [msg[req_id][12:]]
            req_id += 1
            while (req_id < len(msg)) and (msg[req_id][:12] == ' '*12):
                requestors.append(msg[req_id][12:])
                req_id += 1
            pairs['Requestors'] = requestors
            for i in range(req_id,len(msg)):
                colon = msg[i].find(': ')
                if colon > 0:
                    pairs[msg[i][:colon].strip()] = msg[i][colon+1:].strip()
            pairs['id'] = ticket_id
            return pairs
        else:
            raise Exception('Connection error')

    def create_ticket(self, Queue=DEFAULT_QUEUE, **kwargs):
        """ Create new ticket and set given parameters.
        
        Example of message sended to ``http://tracker.example.com/REST/1.0/ticket/new``::

            content=id: ticket/new
            Queue: General
            Owner: Nobody
            Requestors: somebody@example.com
            Subject: Ticket created through REST API
            Text: Lorem Ipsum
    
        In case of success returned message has this form::

            RT/3.8.7 200 Ok
    
            # Ticket 123456 created.
            # Ticket 123456 updated.
    
        Otherwise::

            RT/3.8.7 200 Ok

            # Required: id, Queue
    
        + list of some key, value pairs, probably default values.
        
        :keyword Queue: Queue where to create ticket
        :keyword kwargs: Other arguments possible to set:
                         
                         Requestors, Subject, Cc, AdminCc, Owner, Status,
                         Priority, InitialPriority, FinalPriority,
                         TimeEstimated, Starts, Due, Text,... (according to RT
                         fields)

                         Custom fields CF.{<CustomFieldName>} could be set
                         with keywords CF_CustomFieldName.
        :returns: ID of new ticket or ``-1``, if creating failed
        """

        post_data = 'id: ticket/new\nQueue: %s\n'%(Queue)
        for key in kwargs:
            if key[:3] != 'CF_':
                post_data += "%s: %s\n"%(key, kwargs[key])
            else:
                post_data += "CF.{%s}: %s\n"%(key[3:], kwargs[key])
        msg = self.__request('ticket/new', {'content':post_data})
        state = msg.split('\n')[2]
        res = re.search(' [0-9]+ ',state)
        if res is not None:
            return int(state[res.start():res.end()])
        else:
            return -1

    def edit_ticket(self, ticket_id, **kwargs):
        """ Edit ticket values.
    
        :param ticket_id: ID of ticket to edit
        :keyword kwargs: Other arguments possible to set:
                         
                         Requestors, Subject, Cc, AdminCc, Owner, Status,
                         Priority, InitialPriority, FinalPriority,
                         TimeEstimated, Starts, Due, Text,... (according to RT
                         fields)

                         Custom fields CF.{<CustomFieldName>} could be set
                         with keywords CF_CustomFieldName.
        :returns: ``True``
                      Operation was successful
                  ``False``
                      Ticket with given ID does not exist or unknown parameter
                      was set (in this case all other valid fields are changed)
        """
        post_data = ''
        for key in kwargs:
            if key[:3] != 'CF_':
                post_data += "%s: %s\n"%(key, kwargs[key])
            else:
                post_data += "CF.{%s}: %s\n" % (key[3:], kwargs[key])
        msg = self.__request('ticket/%s/edit' % (str(ticket_id)), {'content':post_data})
        state = msg.split('\n')[2]
        if not hasattr(self, 'update_pattern'):
            self.update_pattern = re.compile('^# Ticket [0-9]+ updated.$')
        return self.update_pattern.match(state) is not None

    def get_history(self, ticket_id, transaction_id=None):
        """ Get set of history items.
        
        :param ticket_id: ID of ticket
        :keyword transaction_id: If set to None, all history items are
                                 returned, if set to ID of valid transaction
                                 just one history item is returned
                          
        :returns: List of history items ordered increasingly by time of event.
                  Each history item is dictionary with following keys:

                  Description, Creator, Data, Created, TimeTaken, NewValue,
                  Content, Field, OldValue, Ticket, Type, id, Attachments

                  All these fields are strings, just 'Attachments' holds list
                  of pairs (attachment_id,filename_with_size).
        :raises Exception: Unexpected format of returned message.
        """
        items = []
        try:
            if transaction_id is None:
                # We are using "long" format to get all history items at once.
                # Each history item is then separated by double dash.
                msgs = self.__request('ticket/%s/history?format=l' % (str(ticket_id),))
            else:
                msgs = self.__request('ticket/%s/history/id/%s' % (str(ticket_id), str(transaction_id)))
            msgs = msgs.split('\n--\n')
            if not hasattr(self, 'content_pattern'):
                self.content_pattern = re.compile('Content:')
            if not hasattr(self, 'attachments_pattern'):
                self.attachments_pattern = re.compile('Attachments:')
            for i in range(len(msgs)):
                pairs = {}
                msg = msgs[i].split('\n')
                cont_id = [id for id in range(len(msg)) if self.content_pattern.match(msg[id]) is not None]
                if len(cont_id) == 0:
                    raise Exception('Unexpected history entry. \
                                     Missing line starting with `Content:`.')
                else:
                    cont_id = cont_id[0]
                atta_id = [id for id in range(len(msg)) if self.attachments_pattern.match(msg[id]) is not None]
                if len(atta_id) == 0:
                    raise Exception('Unexpected attachment part of history entry. \
                                     Missing line starting with `Attachements:`.')
                else:
                    atta_id = atta_id[0]
                for i in range(cont_id):
                    colon = msg[i].find(': ')
                    if colon > 0:
                        pairs[msg[i][:colon].strip()] = msg[i][colon + 1:].strip()
                content = msg[cont_id][9:]
                cont_id += 1
                while (cont_id < len(msg)) and (msg[cont_id][:9] == ' ' * 9):
                    content += '\n'+msg[cont_id][9:]
                    cont_id += 1
                pairs['Content'] = content
                for i in range(cont_id, atta_id):
                    colon = msg[i].find(': ')
                    if colon > 0:
                        pairs[msg[i][:colon].strip()] = msg[i][colon + 1:].strip()
                attachments = []
                for i in range(atta_id + 1, len(msg)):
                    colon = msg[i].find(': ')
                    if colon > 0:
                        attachments.append((int(msg[i][:colon].strip()),
                                            msg[i][colon + 1:].strip()))
                pairs['Attachments'] = attachments
                items.append(pairs)    
            return items
        except:
            return []
    
    def reply(self, ticket_id, text='', cc='', bcc='', files=[]):
        """ Sends email message to the contacts in ``Requestors`` field of
        given ticket with subject as is set in ``Subject`` field.

        Form of message according to documentation::

            id: <ticket-id>
            Action: correspond
            Text: the text comment
                  second line starts with the same indentation as first
            Cc: <...>
            Bcc: <...>
            TimeWorked: <...>
            Attachment: an attachment filename/path

        :param ticket_id: ID of ticket to which message belongs
        :keyword text: Content of email message
        :keyword cc: Carbon copy just for this reply
        :keyword bcc: Blind carbon copy just for this reply
        :keyword files: List of pairs (filename, file-like object) describing
                        files to attach as multipart/form-data
        :returns: ``True``
                      Operation was successful
                  ``False``
                      Sending failed (status code != 200)
        """
        post_data = {'content':"""id: %s
Action: correspond
Text: %s
Cc: %s
Bcc: %s"""%(str(ticket_id), re.sub(r'\n', r'\n      ', text), cc, bcc)}
        for file_pair in files:
            post_data['content'] += "\nAttachment: %s" % (file_pair[0],)
        msg = self.__request('ticket/%s/comment' % (str(ticket_id),),
                             post_data, files)
        return self.__get_status_code(msg) == 200

    def comment(self, ticket_id, text='', time_worked=0, cc='', bcc='', files=[]):
        """ Adds comment to the given ticket.
        
        Form of message according to documentation::

            id: <ticket-id>
            Action: comment
            Text: the text comment
                  second line starts with the same indentation as first
            Attachment: an attachment filename/path

        :param ticket_id: ID of ticket to which comment belongs
        :keyword text: Content of comment
        :keyword files: List of pairs (filename, file-like object) describing
                        files to attach as multipart/form-data
        :returns: ``True``
                      Operation was successful
                  ``False``
                      Sending failed (status code != 200)
        """
        post_data = {'content':"""id: %s
Action: comment
TimeWorked: %s
Text: %s""" % (str(ticket_id), time_worked, re.sub(r'\n', r'\n      ', text))}
        for file_pair in files:
            post_data['content'] += "\nAttachment: %s" % (file_pair[0],)
        msg = self.__request('ticket/%s/comment' % (str(ticket_id),),
                             post_data, files)
        return self.__get_status_code(msg) == 200


    def get_attachments_ids(self, ticket_id):
        """ Get IDs of attachments for given ticket.
        
        :param ticket_id: ID of ticket
        :returns: List of IDs (type int) of attachments belonging to given
                  ticket
        """
        at = self.__request('ticket/%s/attachments' % (str(ticket_id),))
        if (len(at) != 0) and (self.__get_status_code(at) == 200):
            atlines = at.split('\n')
            if len(atlines) >= 4:
                return [int(re.sub(r'[^0-9]*([0-9]+):.*', r'\1', line)) for line in atlines[4:] if len(line) > 0]
            else:
                return []
        else:
            return []
        
    def get_attachment(self, ticket_id, attachment_id):
        """ Get attachment.
        
        :param ticket_id: ID of ticket
        :param attachment_id: ID of attachment for obtain
        :returns: Attachment as dictionary with these keys:

                      * Transaction
                      * ContentType
                      * Parent
                      * Creator
                      * Created
                      * Filename
                      * Content
                      * Headers
                      * MessageId
                      * ContentEncoding
                      * id
                      * Subject

                  All these fields are strings, just 'Headers' holds another
                  dictionary with attachment headers as strings e.g.:
                  
                      * Delivered-To
                      * From
                      * Return-Path
                      * Content-Length
                      * To
                      * X-Seznam-User
                      * X-QM-Mark
                      * Domainkey-Signature
                      * RT-Message-ID
                      * X-RT-Incoming-Encryption
                      * X-Original-To
                      * Message-ID
                      * X-Spam-Status
                      * In-Reply-To
                      * Date
                      * Received
                      * X-Country
                      * X-Spam-Checker-Version
                      * X-Abuse
                      * MIME-Version
                      * Content-Type
                      * Subject

                  .. warning:: Content-Length parameter is set after opening
                               ticket in web interface!

                  Set of headers available depends on mailservers sending
                  emails not on Request Tracker!
        :raises Exception: Unexpected format of returned message.
        """
        msg = self.__request('ticket/%s/attachments/%s' % (str(ticket_id), str(attachment_id)))
        msg = msg.split('\n')[2:]
        if not hasattr(self, 'headers_pattern'):
            self.headers_pattern = re.compile('Headers:')
        head_id = [id for id in range(len(msg)) if self.headers_pattern.match(msg[id]) is not None]
        if len(head_id) == 0:
            raise Exception('Unexpected headers part of attachment entry. \
                             Missing line starting with `Headers:`.')
        else:
            head_id = head_id[0]
        msg[head_id] = re.sub(r'^Headers: (.*)$', r'\1', msg[head_id])
        if not hasattr(self, 'content_pattern'):
            self.content_pattern = re.compile('Content:')
        cont_id = [id for id in range(len(msg)) if self.content_pattern.match(msg[id]) is not None]
        
        if len(cont_id) == 0:
            raise Exception('Unexpected content part of attachment entry. \
                             Missing line starting with `Content:`.')
        else:
            cont_id = cont_id[0]
        pairs = {}
        for i in range(head_id):
            colon = msg[i].find(': ')
            if colon > 0:
                pairs[msg[i][:colon].strip()] = msg[i][colon + 1:].strip()
        headers = {}
        for i in range(head_id, cont_id):
            colon = msg[i].find(': ')
            if colon > 0:
                headers[msg[i][:colon].strip()] = msg[i][colon + 1:].strip()
        pairs['Headers'] = headers
        content = msg[cont_id][9:]
        for i in range(cont_id+1, len(msg)):
            if msg[i][:9] == (' ' * 9):
                content += '\n' + msg[i][9:]
        pairs['Content'] = content
        return pairs

    def get_attachment_content(self, ticket_id, attachment_id):
        """ Get content of attachment without headers.

        This function is necessary to use for binary attachment,
        as it can contain ``\\n`` chars, which would disrupt parsing
        of message if :py:meth:`~Rt.get_attachment` is used.
        
        Format of message::

            RT/3.8.7 200 Ok\n\nStart of the content...End of the content\n\n\n
        
        :param ticket_id: ID of ticket
        :param attachment_id: ID of attachment
        
        Returns: string with content of attachment
        """
    
        msg = self.__request('ticket/%s/attachments/%s/content' % (str(ticket_id), str(attachment_id)))
        return msg[re.search(b'\n', msg).start() + 2:-3]

    def get_user(self, user_id):
        """ Get user details.
        
        :param user_id: Identification of user by username (str) or user ID
                        (int)
        :returns: User details as strings in dictionary with these keys for RT
                  users:

                      * Lang
                      * RealName
                      * Privileged
                      * Disabled
                      * Gecos
                      * EmailAddress
                      * Password
                      * id
                      * Name

                  Or these keys for external users (e.g. Requestors replying
                  to email from RT:

                      * RealName
                      * Disabled
                      * EmailAddress
                      * Password
                      * id
                      * Name
        :raises Exception: In case that returned status code is not 200
        """
        msg = self.__request('user/%s' % (str(user_id),))

        if(self.__get_status_code(msg) == 200):
            pairs = {}
            msg = msg.split('\n')[2:]
            for i in range(len(msg)):
                colon = msg[i].find(': ')
                if colon > 0:
                    pairs[msg[i][:colon].strip()] = msg[i][colon + 1:].strip()
            return pairs
        else:
            raise Exception('Connection error')

    def get_queue(self, queue_id):
        """ Get queue details.
        
        :param queue_id: Identification of queue by name (str) or queue ID
                        (int)
        :returns: Queue details as strings in dictionary with these keys
                  (if queue exists):

                      * id
                      * Name
                      * Description
                      * CorrespondAddress
                      * CommentAddress
                      * InitialPriority
                      * FinalPriority
                      * DefaultDueIn

        :raises Exception: In case that returned status code is not 200
        """
        msg = self.__request('queue/%s' % str(queue_id))

        if(self.__get_status_code(msg) == 200):
            pairs = {}
            msg = msg.split('\n')[2:]
            for i in range(len(msg)):
                colon = msg[i].find(': ')
                if colon > 0:
                    pairs[msg[i][:colon].strip()] = msg[i][colon + 1:].strip()
            return pairs
        else:
            raise Exception('Connection error')

    def get_links(self, ticket_id):
        """ Gets the ticket links for a single ticket.
        
        :param ticket_id: ticket ID
        :returns: Links as lists of strings in dictionary with these keys
                  (just those which are defined):

                      * id
                      * Members
                      * MemberOf
                      * RefersTo
                      * ReferredToBy
                      * DependsOn
                      * DependedOnBy

        :raises Exception: In case that returned status code is not 200
        """
        msg = self.__request('ticket/%s/links/show' % (str(ticket_id),))

        if(self.__get_status_code(msg) == 200):
            pairs = {}
            msg = msg.split('\n')[2:]
            i = 0
            while i < len(msg):
                colon = msg[i].find(': ')
                if colon > 0:
                    key = msg[i][:colon]
                    links = [msg[i][colon + 1:].strip()]
                    j = i + 1
                    pad = len(key) + 2
                    # loop over next lines for the same key 
                    while (j < len(msg)) and msg[j].startswith(' ' * pad):
                        links[-1] = links[-1][:-1] # remove trailing comma from previous item
                        links.append(msg[j][pad:].strip())
                        j += 1
                    pairs[key] = links
                    i = j - 1
                i += 1
            return pairs
        else:
            raise Exception('Connection error')

    def edit_ticket_links(self, ticket_id, **kwargs):
        """ Edit ticket links.
    
        :param ticket_id: ID of ticket to edit
        :keyword kwargs: Other arguments possible to set: DependsOn,
                         DependedOnBy, RefersTo, ReferredToBy, Members,
                         MemberOf. Each value should be either ticker ID or
                         external link. Int types are converted. Use empty
                         string as value to delete existing link.
        :returns: ``True``
                      Operation was successful
                  ``False``
                      Ticket with given ID does not exist or unknown parameter
                      was set (in this case all other valid fields are changed)
        """
        post_data = ''
        for key in kwargs:
            post_data += "%s: %s\n"%(key, str(kwargs[key]))
        msg = self.__request('ticket/%s/links' % (str(ticket_id),),
                             {'content':post_data})
        state = msg.split('\n')[2]
        if not hasattr(self, 'links_updated_pattern'):
            self.links_updated_pattern = re.compile('^# Links for ticket [0-9]+ updated.$')
        return self.links_updated_pattern.match(state) is not None

    def merge_ticket(self, ticket_id, into_id):
        """ Merge ticket into another (undocumented API feature). May not work
        in 4.x RT series.
    
        :param ticket_id: ID of ticket to be merged
        :param into: ID of destination ticket
        :returns: ``True``
                      Operation was successful
                  ``False``
                      Either origin or destination ticket does not
                      exist or user does not have ModifyTicket permission.
        """
        msg = self.__request('ticket/merge/%s' % (str(ticket_id),),
                             {'into':into_id})
        state = msg.split('\n')[2]
        if not hasattr(self, 'merge_successful_pattern'):
            self.merge_successful_pattern = re.compile('^Merge Successful$')
        return self.merge_successful_pattern.match(state) is not None

