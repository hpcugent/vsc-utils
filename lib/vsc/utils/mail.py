#!/usr/bin/env python
##
#
# Copyright 2012 Andy Georges
#
# This file is part of the tools originally by the HPC team of
# Ghent University (http://ugent.be/hpc).
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
"""This file contains functionality to send emails from within the various VSC python tools.

@author Andy Georges

Created Apr 11, 2012
"""

import smtplib
from email.MIMEText import MIMEText

import vsc.fancylogger as fancylogger
from vsc.exceptions import VscError


class VscMailError(VscError):
    """When sending a mail goes wrong."""

    def __init__(self, mail_host=None, mail_to=None, mail_from=None, mail_subject=None, err=None):
        """Initializer.

        @type err: the original exception, if any.
        """
        VscError.__init__(self)
        self.mail_host = mail_host
        self.mail_to = mail_to
        self.mail_from = mail_from
        self.mail_subject = mail_subject
        self.err = err


class VscMail(object):
    """Class to send out mail."""

    def __init__(self, mail_host=None):
        self.mail_host = mail_host
        self.logger = fancylogger.getLogger(self.__class__.__name__)

    def sendTextMail( self
                    , mail_to="hpc-admin@lists.ugent.be"
                    , mail_from="HPC-admin"
                    , reply_to=None
                    , subject=""
                    , message=""):
        """Send out the given message by mail to the given recipient(s).

        @type mail_to: a string or a list of strings representing one or more valid email addresses
        @type mail_from: string representing a valid email address
        @type reply_to: a string representing a valid email address for the (potential) replies
        @type message: a string representing the body of the mail
        """
        self.logger.info("Sending mail [%s] to %s." % (subject, mail_to))

        if reply_to is None:
            reply_to = mail_from
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = mail_from
        msg['To'] = mail_to
        msg['Reply-to'] = reply_to

        try:
            if self.mail_host:
                s = smtplib.SMTP(self.mail_host)
            else:
                s = smtplib.SMTP()
            s.connect()
            try:
                s.sendmail(mail_from, mail_to, msg.as_string())
            except smtplib.SMTPHeloError, err:
                self.logger.error("Cannot get a proper response from the SMTP host"
                           + (self.mail_host and " %s" % (self.mail_host) or ""))
                raise
            except smtplib.SMTPRecipientsRefused, err:
                self.logger.error("All recipients were refused by SMTP host"
                           + (self.mail_host and " %s" % (self.mail_host) or "")
                           + " [%s]" % (mail_to))
                raise
            except smtplib.SMTPSenderRefused, err:
                self.logger.error("Sender was refused by SMTP host"
                           + (self.mail_host and " %s" % (self.mail_host) or "")
                           + "%s" % (mail_from))
                raise
            except smtplib.SMTPDataError, err:
                raise
        except smtplib.SMTPConnectError, err:
            self.logger.error("Cannot connect to the SMTP host" + (self.mail_host and " %s" % (self.mail_host) or ""))
            raise VscMailError( mail_host=self.mail_host
                              , mail_to=mail_to
                              , mail_from=mail_from
                              , mail_subject=subject
                              , err=err)
        except Exception, err:
            self.logger.error("Some unknown exception occurred in VscMail.sendTextMail. Raising a VscMailError.")
            raise VscMailError( mail_host=self.mail_host
                              , mail_to=mail_to
                              , mail_from=mail_from
                              , mail_subject=subject
                              , err=err)
