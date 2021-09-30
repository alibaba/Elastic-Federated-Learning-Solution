import React from 'react';
type Context ={
    projectConfig?:object
};
const defatutContext:Context = {};
const ProjectContext = React.createContext(defatutContext);

export default ProjectContext;