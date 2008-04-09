EDS_AVAILABLE = False
try:
    import evolution
    from evolution import ecal
    EDS_AVAILABLE = True
except:
    pass

def get_eds_tasks():
    if not EDS_AVAILABLE:
        return []
    sources = ecal.list_task_sources()
    tasks = []
    for source in sources:
        data = ecal.open_calendar_source(source[1], ecal.CAL_SOURCE_TYPE_TODO)
        if data:
            for task in data.get_all_objects():
                if task.get_status() in [ecal.AL_STATUS_NONE, ecal.AL_STATUS_INPROCESS]:
                    tasks.append({'name': task.get_summary()})
    return tasks
