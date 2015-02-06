#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
'''
Script Name:     aws-event-monitoring.py

Author:          run2cmd

Requirements:    Python 2.6 or higher (not tested with python3)
                 Boto.ec2 python library
                 AWS connfiguration in /etc/boto.cfg (Key + Secret)

Version:         0.1 - Initial version        
'''                                                   
import boto.ec2
import datetime
import os.path
import json
import argparse
import sys

class EventParse():

    def __init__(self, aws_region):
        #self.ec2_conn = boto.ec2.connect_to_region(aws_region, aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
        self.ec2_conn = boto.ec2.connect_to_region(aws_region)
        self.ec2_all_statuses = self.ec2_conn.get_all_instance_status()
        self.new_events = []
        self.old_events = []
        self.new2add = []
        self.send_code = []

    def check_file(self, fname):
        if os.path.exists(fname):
            pass
        else:
            print 'ERROR: %s file is missing' % (fname)
            quit()
        
    # Find new events
    def find_events(self):
        for ec2_status in self.ec2_all_statuses:
            if ec2_status.events != None:
                for event in ec2_status.events:
                    desc = str(event.description)
                    inst_id = str(ec2_status.id)
                    code = str(event.code)
                    # Convert time to more readable output
                    if 'None' not in str(event.not_after):
                        date_after = str(datetime.datetime.strptime(str(event.not_after).replace('T', ' ').replace('Z', ''), "%Y-%m-%d %H:%M:%S.%f"))
                    else:
                        date_after = 'None'
                    if 'None' not in str(event.not_after):
                        date_before = str(datetime.datetime.strptime(str(event.not_before).replace('T', ' ').replace('Z', ''), "%Y-%m-%d %H:%M:%S.%f"))
                    else:
                        date_before = 'None'
                    # Fromat that to dictionary so variables can be reached easier: {ID, Code, Date Start, Date End}
                    self.new_events.append({ 'ID': inst_id, 'Code': code, 'Date Start': date_after, 'Date End': date_before, 'Description': desc })
    
    # Get old events from json file so we won't alert something that was alerted already
    def get_old_events(self, fname):
        if os.path.exists(fname):
            file = open(fname, 'r+')
            # Import data from json file. This way you can assing data to variable.
            self.old_events = json.load(file)        
            file.close()
        else:
            file = open(fname, 'w+')
            # Put data to json file for better data input and output
            json.dump(self.new_events, file)
            self.send_code.append('noFILE')
            file.close()
    
    # Compare new events with old ones if they exists.
    # This is one way comparision new vs. old
    def diff_events(self):
        if len(self.new_events) > 0:
            if len(self.old_events) > 0:
                for each_new_event in self.new_events:
                    if each_new_event in self.old_events:
                        pass
                    else:
                        self.send_code.append('newEVENT')
                        self.new2add.append(each_new_event)
                if 'newEVENT' not in self.send_code:
                    self.send_code.append('noEVENT')
            else:
                for item in self.new_events:
                    self.new2add.append(item)
                self.send_code.append('newEVENT')
        else:
            self.send_code.append('noEVENT')
    
    # Setup alert code for Icinga
    def set_code(self):
        if self.send_code[0] == 'noEVENT':
            print 'OK: No new events'
            sys.exit(0)
        else:
            if self.send_code[0] == 'noFILE':
                print 'WARNING: Event file was missing. All events set to new:',
            elif self.send_code[0] == 'newEVENT':
                print 'WARNING: New Events:',
            for event in self.new2add:
                this_instance = self.ec2_conn.get_only_instances(instance_ids=event['ID'])
                this_name = this_instance[0].tags['Name']
                print '####  %s  -  %s  -  Start: %s  -  End: %s  -  %s' % (this_name, event['Code'], event['Date Start'], event['Date End'], str(event['Description'])),
            sys.exit(1)
    
    # Remove old alerts and put new ones
    def clean_up(self, fname):
        file = open(fname, 'w+')
        json.dump(self.new_events, file)
        file.close()
                
                                
if __name__ == '__main__':
    # Some Const Variables:
    working_file = 'event.json'
    cfg_file = '/etc/boto.cfg'
    os.chdir('/u01/icinga/etc')

    # Add script description and command line arguments
    parser = argparse.ArgumentParser(description='This is AWS Event monitoring script. It will send WARNING alert each time new event will be detected. Old events are in event.json file in /usr/lib64/nagios/plugins.\nCreated by run2cmd.')
    parser.add_argument('-r', type=str, help='Region name, ex: eu-west-1', required=True)
    args = parser.parse_args()
    region = args.r

    # Core
    evp = EventParse(region)
    evp.check_file(cfg_file)
    evp.find_events()    
    evp.get_old_events(working_file) 
    evp.diff_events()
    evp.clean_up(working_file)
    evp.set_code()
