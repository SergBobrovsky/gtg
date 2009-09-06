import os
import sys
import time
import subprocess
import gobject
from xdg.BaseDirectory import xdg_config_home, xdg_cache_home
import xml.utils.iso8601
from datetime import date

#This add's the plugin's path to python sys path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))+'/pyrtm')
import rtm
import utility
from generic_task import RtmTask
from generic_proxy import GenericProxy



class RtmProxy(GenericProxy):
    def __init__(self):
        super(RtmProxy, self).__init__()
        self.token = None

    def getToken(self):
        """gets a token from file (if a previous sync has been
            performed), or opens a browser to request a new one
            (in which case the function returns true). NOTE: token 
            is valid forever """
        if self.token == None:
            self.config_dir = os.path.join(xdg_config_home,'gtg/plugins/rtm-sync')
            self.token = utility.smartLoadFromFile (self.config_dir, 'token')
        if self.token == None:
            self.rtm=rtm.createRTM ("2a440fdfe9d890c343c25a91afd84c7e", \
                                   "ca078fee48d0bbfa");
            subprocess.Popen(['xdg-open', self.rtm.getAuthURL()])
            return False
        return True

    def login(self):
        #TODO:  handling connection failures and denial of access, proper interface 
        #       assert (self.token != None), "Token must be requested before 
        #       calling synchronize"
        if hasattr(self,'rtm'):
                self.token = self.rtm.getToken()
        if (self.getToken() == False):
            return False
        self.rtm=rtm.createRTM ("2a440fdfe9d890c343c25a91afd84c7e",\
                               "ca078fee48d0bbfa", self.token );
        utility.smartSaveToFile(self.config_dir,'token', self.token)
        #NOTE: a timeline is an undo list for RTM. It can be used for journaling
        #      (timeline rollback is atomical)
        self.timeline = self.rtm.timelines.create().timeline
        return True

    def generateTaskList(self):
        #NOTE: syncing only incomplete tasks for now
        #(it's easier to debug the things you see)
        lists_id_list = map (lambda x: x.id,self.rtm.lists.getList().lists.list)
        def get_list_of_taskseries (x): 
            currentlist = self.rtm.tasks.getList\
                    (filter='status:incomplete',list_id=x).tasks
            if hasattr (currentlist, 'list'):
                return currentlist.list
            else:
                return []
        task_list_global= map (get_list_of_taskseries,lists_id_list)
        taskseries_list = filter(lambda x: hasattr (x[0],'taskseries')\
                                 , zip(task_list_global,lists_id_list))
        tasks_list_wrapped = map (lambda x: (x[0].taskseries,x[1]), taskseries_list)
        tasks_list_normalized = map(lambda x:  zip(x[0],[x[1]]*len(x[0]), \
                map(lambda x: x.id,x[0])) if type(x[0]) == list \
                else [(x[0],x[1],x[0].id)] ,tasks_list_wrapped)
        tasks_list_unwrapped = []
        task_objects_list = []
        list_ids_list = []
        taskseries_ids_list = []
        if len(tasks_list_normalized)>0:
            tasks_list_unwrapped = reduce(lambda x,y: x+y , tasks_list_normalized)
            task_objects_list,list_ids_list,taskseries_ids_list = \
                    utility.unziplist(tasks_list_unwrapped)

        for task,list_id,taskseries_id in  \
            zip(task_objects_list, list_ids_list, taskseries_ids_list):
            self.task_list.append(RtmTask(task, list_id, taskseries_id, \
                                          self.rtm, self.timeline))

    def newTask(self, title):
        #FIXME: possible bug? Don't know list_id, taskseries_id. Should 
        #       never raise, though
        new_task= RtmTask(self.rtm.tasks.add(timeline=self.timeline, name=title)\
                        .list.taskseries.task,None,None, self.rtm, self.timeline)
        self.task_list.append(new_task)
        return new_task
        



