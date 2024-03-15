import { service } from '@/utils/request'

export const getTodoItems = (groupId, params) => {
    return service({
        url: '/todo/' + groupId,
        method: 'get',
        params: params
    })
}

export const createTodoItem = (data) => {
    return service({
        url: '/todo/item/',
        method: 'post',
        data: data
    })
}

export const updateTodoItem = (data) => {
    return service({
        url: '/todo/item/',
        method: 'put',
        data: data
    })
}

export const deleteTodoItem = (todoId) => {
    return service({
        url: '/todo/item/' + todoId,
        method: 'delete',
    })
}