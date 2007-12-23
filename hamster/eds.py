EDS_AVAILABLE = False
try:
    import evolution
    EDS_AVAILABLE = True
except:
    pass

def get_eds_tasks():
    if not EDS_AVAILABLE:
        return []
    sources = evolution.ecal.list_task_sources()
    tasks = []
    for source in sources:
        data = evolution.ecal.open_calendar_source(source[1], evolution.ecal.CAL_SOURCE_TYPE_TODO)
        if data:
            for task in data.get_all_objects():
                tasks.append(task.get_summary())
    return tasks

