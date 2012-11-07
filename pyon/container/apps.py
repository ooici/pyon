#!/usr/bin/env python

"""Part of the container that manages rels, apps, processes etc."""

__author__ = 'Michael Meisinger'

from copy import deepcopy
from pyon.core.exception import ContainerAppError, ConfigNotFound
from pyon.util.config import Config
from pyon.util.containers import DotDict, named_any, dict_merge
from pyon.util.log import log


START_PERMANENT = "permanent"


class AppManager(object):
    def __init__(self, container):
        self.container = container
        self.apps = []

    def start(self):
        log.debug("AppManager starting ...")

    def stop(self):
        log.debug("AppManager stopping ...")
        # Stop apps in reverse order of startup
        for appdef in reversed(self.apps):
            self.stop_app(appdef)
        log.debug("AppManager stopped, OK.")

    def start_rel_from_url(self, rel_url="", config=None):
        """
        @brief Read the rel file and call start_rel
        """
        log.info("AppManager.start_rel_from_url(rel_url=%s) ...", rel_url)

        try:
            rel = Config([rel_url]).data
            self.start_rel(rel, config)
            log.debug("AppManager.start_rel_from_url(rel_url=%s) done,  OK.", rel_url)
            return True
        except ConfigNotFound as cnf:
            log.warning("Could not find container deploy file '%s'", rel_url)
        except Exception as ex:
            log.exception("Could not start container deploy file '%s'", rel_url)
            raise ContainerAppError(ex.message)

        return False

    def start_rel(self, rel=None, config=None):
        """
        @brief Recurse over the rel and start apps defined there.
        Note: apps in a rel file can come in one of 2 forms:
        1 processapp: In-line defined process to be started as app
        2 app file: Reference to an app definition in an app file
        If the rel file provides an app config block, it is provided to spawn the process.
        Any given function config dict is merged on top of this.
        """
        log.debug("AppManager.start_rel(rel=%s) ...", rel)

        if rel is None:
            rel = {}

        for rel_app_cfg in rel.apps:
            name = rel_app_cfg.name
            log.debug("app definition in rel: %s" % str(rel_app_cfg))

            if 'processapp' in rel_app_cfg:
                # Case 1: Rel contains definition of process to start as app
                name, module, cls = rel_app_cfg.processapp

                rel_cfg = None
                if 'config' in rel_app_cfg:
                    rel_cfg = deepcopy(rel_app_cfg.config)
                    if config:
                        dict_merge(rel_cfg, config, inplace=True)

                self.container.spawn_process(name, module, cls, rel_cfg)
                self.apps.append(DotDict(type="application", name=name, processapp=rel_app_cfg.processapp))

            else:
                # Case 2: Rel contains reference to app file to start
                app_file_path = 'res/apps/%s.yml' % (name)
                rel_cfg = rel_app_cfg.get('config', None)
                if config:
                    dict_merge(rel_cfg, config, inplace=True)
                self.start_app_from_url(app_file_path, config=rel_cfg)

    def start_app_from_url(self, app_url="", config=None):
        """
        @brief Read the app file and call start_app
        """
        log.debug("AppManager.start_app_from_url(app_url=%s) ..." % app_url)

        try:
            app = Config([app_url]).data
            self.start_app(appdef=app, config=config)
            return True
        except ConfigNotFound as cnf:
            log.warning("Could not find container app file '%s'" % app_url)
        except Exception as ex:
            log.exception("Could not start app file %s" % app_url)
            raise ContainerAppError(ex.message)

        return False

    def start_app(self, appdef=None, config=None):
        """
        @brief Start an app from an app definition.
        Note: apps can come in one of 2 variants:
        1 processapp: In-line defined process to be started
        2 regular app: Full app definition
        """
        log.debug("AppManager.start_app(appdef=%s) ..." % appdef)

        appdef = DotDict(appdef)

        if 'config' in appdef:
            app_cfg = deepcopy(appdef.config)
            if config:
                dict_merge(app_cfg, config, inplace=True)
            config = app_cfg

        if 'processapp' in appdef:
            # Case 1: Appdef contains definition of process to start
            name, module, cls = appdef.processapp
            try:
                pid = self.container.spawn_process(name, module, cls, config)
                appdef._pid = pid
                self.apps.append(appdef)
            except Exception:
                log.exception("Appl %s start from processapp failed" % appdef.name)
        else:
            # Case 2: Appdef contains full app start params
            modpath = appdef.mod
            try:
                mod = named_any(modpath)
                appdef._mod_loaded = mod

                # Start the app
                supid, state = mod.start(self.container, START_PERMANENT, appdef, config)
                appdef._supid = supid
                appdef._state = state

                log.debug("App '%s' started. Root sup-id=%s" % (appdef.name, supid))

                self.apps.append(appdef)
            except Exception:
                log.exception("Appl %s start from appdef failed" % appdef.name)

    def stop_app(self, appdef):
        log.debug("App '%s' stopping" % appdef.name)
        try:
            if '_mod_loaded' in appdef:
                appdef._mod_loaded.stop(self.container, appdef._state)
        except Exception, ex:
            log.exception("Application %s stop failed" % appdef.name)
